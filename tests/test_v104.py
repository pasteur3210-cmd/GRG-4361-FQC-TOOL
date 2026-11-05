from grg4361 import check_tx_power,assess,Inspector
from test_grg4361 import device_html,parse_device
from pathlib import Path
from openpyxl import load_workbook
from master_record import sync_master, MASTER_NAME
from main import save_record

def test_tx_limits():
    assert check_tx_power('6.8 dBm')=='PASS'
    assert check_tx_power('7.2 dBm')=='PASS'
    assert check_tx_power('6.799 dBm')=='FAIL'
    assert check_tx_power('7.201 dBm')=='FAIL'
    assert check_tx_power('No signal')=='FAIL'
    assert check_tx_power('7.0 V')=='ERROR'

def test_three_barcode_checks_and_o5():
    device=parse_device(device_html())
    pon={'Temperature':'40 C','Voltage':'3.3 V','Tx Power':'7.0 dBm','Rx Power':'-18 dBm','Bias Current':'12 mA','ONU State':'O5'}
    scans={'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'}
    overall,rows=assess(device,'CMTD0CFFC101',pon,scans,'MTA-1.0.14')
    assert overall=='REVIEW' # SN shipment range still not validated
    assert next(r for r in rows if r['item']=='PON Tx Power')['result']=='PASS'
    assert next(r for r in rows if r['item']=='Label MAC vs DUT MAC')['result']=='PASS'
    scans['mac']='ABCDEF123456'
    overall,rows=assess(device,'CMTD0CFFC101',pon,scans,'MTA-1.0.14')
    assert overall=='FAIL'

def test_inspector_polls_until_o5_only_after_scans(monkeypatch):
    from grg4361 import parse_device
    client=Inspector.__new__(Inspector)
    class Dummy:
        debug=None
        def login(self,*args):pass
    client.client=Dummy()
    events=[]
    def read(path):
        events.append(path)
        if path=='status.asp':return device_html()
        if path=='gpon.asp':return '<tr><th>Serial Number</th><td>CMTD0CFFC101</td></tr>'
        state='O1' if events.count('status_pon.asp')==1 else 'O5'
        return '<table>'+''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k,v in [('Temperature','35 C'),('Voltage','3 V'),('Tx Power','7.0 dBm' if state=='O5' else 'No signal'),('Rx Power','-18 dBm'),('Bias Current','12 mA'),('ONU State',state)])+'</table>'
    client.read=read
    overall,rows,details=client.run('root','test',{'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'},'MTA-1.0.14',poll_interval=0)
    assert events==['status.asp','gpon.asp','status_pon.asp','status_pon.asp']
    assert details['pon']['ONU State']=='O5'
    assert overall=='REVIEW'

def test_master_new_columns_and_append(tmp_path):
    root=tmp_path/'Records';run=root/'run_001';run.mkdir(parents=True)
    scans={'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'}
    rows=[{'item':'LED Initial','expected':'Visual','actual':'PASS','result':'PASS'}, {'item':'LED Functional','expected':'Visual','actual':'PASS','result':'PASS'}, {'item':'PON Tx Power','expected':'6.8-7.2 dBm','actual':'7.0 dBm','result':'PASS'}]
    save_record(run,'REVIEW',rows,{'pon':{},'device':{},'gpon':'CMTD0CFFC101'},scans['sn'],'Worker',scans)
    assert sync_master(root)==1
    assert sync_master(root)==0
    wb=load_workbook(root/MASTER_NAME);ws=wb['All Tests']
    assert ws.cell(2,28).value=='64680CFFC101'
    assert ws.cell(2,30).value=='PASS'
    assert ws.cell(2,32).value=='PASS'
