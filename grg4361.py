"""GRG-4361 read-only FQC verification; PON read occurs only after O5."""
from __future__ import annotations
import re
import time
from bs4 import BeautifulSoup
from router_oqc.client import RouterClient, RouterError

VERSION = 'V1.0.4'
TX_MIN_DBM = 6.8
TX_MAX_DBM = 7.2
WAN_GOLDEN = {
    'nas0_0': ('7','TR069','IPoE'),
    'nas0_1': ('747','VOICE','IPoE'),
    'nas0_2': ('9','Other','Bridged'),
}

def clean(s): return ' '.join(str(s).replace('\xa0',' ').split())
def get_rows(html):
    soup=BeautifulSoup(html,'html.parser'); out={}
    for th in soup.find_all('th'):
        td=th.find_next('td')
        if td: out[clean(th.get_text(' ',strip=True)).rstrip(':')]=clean(td.get_text(' ',strip=True))
    return out

def parse_device(html):
    from router_oqc.parser import _extract_wan_by_rows, _extract_wan_fallback
    soup=BeautifulSoup(html,'html.parser'); fields=get_rows(html)
    row_wan=_extract_wan_by_rows(soup); fallback_wan=_extract_wan_fallback(html)
    wan=max((row_wan,fallback_wan),key=lambda records:len({r.get('Interface') for r in records}))
    missing=[k for k in ('Device Name','Firmware Version','MAC Address') if not fields.get(k)]
    if missing: raise ValueError('Missing device fields: '+','.join(missing))
    if not wan: raise ValueError('Missing WAN Configuration records')
    return {'model':fields['Device Name'],'firmware':fields['Firmware Version'],
            'mac':re.sub('[^0-9A-Fa-f]','',fields['MAC Address']).upper(),'wan':wan}

def parse_gpon(html):
    value=get_rows(html).get('Serial Number','').strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{12}',value): raise ValueError('GPON Serial Number missing or malformed')
    return value

def parse_pon(html):
    fields=get_rows(html)
    needed=('Temperature','Voltage','Tx Power','Rx Power','Bias Current','ONU State')
    missing=[k for k in needed if not fields.get(k)]
    if missing:raise ValueError('Missing PON status: '+','.join(missing))
    return {k:fields.get(k,'') for k in (*needed,'ONU ID','LOID Status')}

def normalize_mac(text):return re.sub('[^0-9A-Fa-f]','',str(text)).upper()
def normalize_gpon(text):return clean(text).upper()
def check_tx_power(reading):
    """Never interpret voltage as optical power: optical Tx is dBm."""
    value=clean(reading)
    if value.lower() in ('no signal','', 'n/a'):return 'FAIL'
    m=re.fullmatch(r'([+-]?\d+(?:\.\d+)?)\s*(dBm)',value,re.I)
    if not m:return 'ERROR'   # Missing/unknown unit is not a valid dBm measurement.
    number=float(m.group(1))
    return 'PASS' if TX_MIN_DBM <= number <= TX_MAX_DBM else 'FAIL'

def assess(device,gpon,pon,scans=None,expected_firmware='',led_initial='PASS',led_functional='PASS'):
    scans=scans or {};rows=[]
    def add(name,expected,actual,result):rows.append({'item':name,'expected':expected,'actual':actual,'result':result})
    add('LED Initial','Visual LED inspection','Operator: '+led_initial,led_initial)
    add('LED Functional','Phone off-hook / PON green after O5','Operator: '+led_functional,led_functional)
    add('Model','GRG-4361',device['model'],'PASS' if device['model']=='GRG-4361' else 'FAIL')
    add('Firmware',expected_firmware or 'Not approved',device['firmware'],('PASS' if device['firmware']==expected_firmware else 'FAIL') if expected_firmware else 'REVIEW')
    sn=scans.get('sn','').strip()
    add('Label SN Format','20 characters',sn or 'Missing','PASS' if len(sn)==20 else 'FAIL')
    add('SN Range','Approved shipment range not supplied',sn or 'Missing','REVIEW')
    mac=device['mac']; label_mac=normalize_mac(scans.get('mac',''))
    add('DUT MAC Format','12 hexadecimal characters',mac,'PASS' if re.fullmatch('[0-9A-F]{12}',mac) else 'FAIL')
    add('Label MAC vs DUT MAC',mac,label_mac or 'Missing','PASS' if label_mac==mac and bool(label_mac) else 'FAIL')
    label_gpon=normalize_gpon(scans.get('gpon',''))
    add('Label GPON SN vs DUT GPON SN',gpon,label_gpon or 'Missing','PASS' if label_gpon==gpon and bool(label_gpon) else 'FAIL')
    expected_gpon='CMTD'+mac[-8:] if len(mac)==12 else 'Unavailable'
    add('GPON SN vs MAC',expected_gpon,gpon,'PASS' if expected_gpon==gpon else 'FAIL')
    actual_wan={r.get('Interface',''):r for r in device['wan']}
    for name,expected in WAN_GOLDEN.items():
        actual=actual_wan.get(name)
        if actual is None: add('WAN '+name,' | '.join(expected),'Missing','FAIL');continue
        value=tuple(actual.get(k,'') for k in ('VLAN ID','Connection Type','Protocol'))
        add('WAN '+name,' | '.join(expected),' | '.join(value),'PASS' if value==expected else 'FAIL')
        add('WAN Link '+name,'Record only',actual.get('Status',''),'INFO')
    onu_state=pon.get('ONU State','NOT READ')
    add('PON ONU State','O5 after fiber connection',onu_state,'PASS' if onu_state.upper()=='O5' else 'FAIL')
    tx=pon.get('Tx Power','NOT READ')
    add('PON Tx Power',f'{TX_MIN_DBM:.1f} to {TX_MAX_DBM:.1f} dBm',tx,check_tx_power(tx) if onu_state.upper()=='O5' else 'FAIL')
    for name,value in pon.items():
        if name in ('ONU State','Tx Power'):continue
        add('PON '+name,'Record only',value,'INFO')
    mandatory=[r['result'] for r in rows if r['result']!='INFO']
    overall='FAIL' if 'FAIL' in mandatory else 'ERROR' if 'ERROR' in mandatory else 'REVIEW' if 'REVIEW' in mandatory else 'PASS'
    return overall,rows

class Inspector:
    def __init__(self,host='192.168.1.1',debug=None):
        self.client=RouterClient(host,protocol='http',debug=debug)
    def close(self):self.client.close()
    def read(self,path):
        response=self.client._get(path)
        if response.status_code!=200 or 'Device Login' in response.text:
            raise RouterError('READ_FAILED','Not authenticated or HTTP error: '+path)
        return response.text
    def run(self,username,password,scans=None,expected_firmware='',led_initial='PASS',led_functional='PASS',
            o5_timeout=60,poll_interval=2):
        self.client.login(username,password)
        if self.client.debug:self.client.debug('HTTP read status.asp START')
        device=parse_device(self.read('status.asp'))
        if self.client.debug:self.client.debug('HTTP read status.asp OK')
        gpon=parse_gpon(self.read('gpon.asp'))
        if self.client.debug:self.client.debug('HTTP read gpon.asp OK; PON status delayed until after fiber connection')
        deadline=time.monotonic()+o5_timeout
        pon={};attempts=0
        while True:
            attempts+=1
            pon=parse_pon(self.read('status_pon.asp'))
            if self.client.debug:self.client.debug('PON ONU State poll #%d: %s'%(attempts,pon['ONU State']))
            if pon['ONU State'].upper()=='O5' or time.monotonic()>=deadline:break
            time.sleep(min(poll_interval,max(0,deadline-time.monotonic())))
        overall,rows=assess(device,gpon,pon,scans,expected_firmware,led_initial,led_functional)
        return overall,rows,{'device':device,'gpon':gpon,'pon':pon,'label_scans':scans or {},'o5_polls':attempts}
