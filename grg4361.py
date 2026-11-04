"""Read-only GRG-4361 inspection engine. No write, reset, or OLT commands."""
from __future__ import annotations
import re
from dataclasses import dataclass
from bs4 import BeautifulSoup
from router_oqc.client import RouterClient, RouterError

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
    row_wan=_extract_wan_by_rows(soup)
    fallback_wan=_extract_wan_fallback(html)
    # Router's malformed table can omit <tr> for the middle WAN entry.
    # Prefer the more complete source-order extraction, not the first nonempty result.
    wan=max((row_wan, fallback_wan), key=lambda records: len({r.get('Interface') for r in records}))
    required=['Device Name','Firmware Version','MAC Address']
    missing=[k for k in required if not fields.get(k)]
    if missing: raise ValueError('Missing device fields: '+','.join(missing))
    if not wan: raise ValueError('Missing WAN Configuration records')
    return {'model':fields['Device Name'],'firmware':fields['Firmware Version'],
            'mac':re.sub('[^0-9A-Fa-f]','',fields['MAC Address']).upper(), 'wan':wan}

def parse_gpon(html):
    fields=get_rows(html)
    value=fields.get('Serial Number','').strip().upper()
    if not value or not re.fullmatch(r'[A-Z0-9]{12}', value): raise ValueError('GPON Serial Number missing or malformed')
    return value

def parse_pon(html):
    fields=get_rows(html)
    needed=('Temperature','Voltage','Tx Power','Rx Power','Bias Current','ONU State')
    missing=[k for k in needed if not fields.get(k)]
    if missing: raise ValueError('Missing PON status: '+','.join(missing))
    return {k:fields.get(k,'') for k in (*needed,'ONU ID','LOID Status')}

def assess(device,gpon,pon,sn='',expected_firmware=''):
    rows=[]
    def add(name,expected,actual,result): rows.append({'item':name,'expected':expected,'actual':actual,'result':result})
    add('Model','GRG-4361',device['model'],'PASS' if device['model']=='GRG-4361' else 'FAIL')
    add('Firmware',expected_firmware or 'Not approved',device['firmware'],('PASS' if device['firmware']==expected_firmware else 'FAIL') if expected_firmware else 'REVIEW')
    add('SN','Scan + approved shipment range required',sn or 'Not scanned','REVIEW')
    mac=device['mac']; add('MAC Format','12 hexadecimal characters',mac,'PASS' if re.fullmatch('[0-9A-F]{12}',mac) else 'FAIL')
    expected_gpon='CMTD'+mac[-8:] if len(mac)==12 else 'Unavailable'
    add('GPON SN vs MAC',expected_gpon,gpon,'PASS' if expected_gpon==gpon else 'FAIL')
    actual_wan={r.get('Interface',''):r for r in device['wan']}
    for name,expected in WAN_GOLDEN.items():
        actual=actual_wan.get(name)
        if actual is None: add('WAN '+name,' | '.join(expected),'Missing','FAIL'); continue
        value=tuple(actual.get(k,'') for k in ('VLAN ID','Connection Type','Protocol'))
        add('WAN '+name,' | '.join(expected),' | '.join(value),'PASS' if value==expected else 'FAIL')
        add('WAN Link '+name,'Record only',actual.get('Status',''),'INFO')
    for name,value in pon.items(): add('PON '+name,'Record only',value,'INFO')
    mandatory=[r['result'] for r in rows if r['result'] not in ('INFO',)]
    overall='FAIL' if 'FAIL' in mandatory else 'REVIEW' if 'REVIEW' in mandatory else 'PASS'
    return overall,rows

class Inspector:
    def __init__(self,host='192.168.1.1',debug=None):
        self.client=RouterClient(host,protocol='http',debug=debug)
    def close(self): self.client.close()
    def run(self,username,password,sn='',expected_firmware=''):
        self.client.login(username,password)
        def read(path):
            response=self.client._get(path)
            if response.status_code!=200 or 'Device Login' in response.text:
                raise RouterError('READ_FAILED','Not authenticated or HTTP error: '+path)
            return response.text
        if self.client.debug: self.client.debug('HTTP read status.asp START')
        device=parse_device(read('status.asp'))
        if self.client.debug: self.client.debug('HTTP read status.asp OK; WAN interfaces: '+','.join(r.get('Interface','') for r in device['wan']))
        if self.client.debug: self.client.debug('HTTP read gpon.asp START')
        gpon=parse_gpon(read('gpon.asp'))
        if self.client.debug: self.client.debug('HTTP read gpon.asp OK')
        if self.client.debug: self.client.debug('HTTP read status_pon.asp START')
        pon=parse_pon(read('status_pon.asp'))
        if self.client.debug: self.client.debug('HTTP read status_pon.asp OK')
        return (*assess(device,gpon,pon,sn,expected_firmware),{'device':device,'gpon':gpon,'pon':pon})
