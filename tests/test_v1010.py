from grg4361 import assess
from router_oqc.lan_port_parser import parse_lan_port_status_html


def html(state):
    return f'<table><tr><td>LAN1 (10GE)</td><td>{state}</td><td><select><option selected>10Gbps Full Duplex</option></select></td></tr></table>'


def test_lan_10g_pass_and_2g_fail():
    for value,speed in [('Up, 10Gb, Full',10000),('Up, 2.5Gb, Full',2500),('Up, 10Gb, Half',10000)]:
        port=parse_lan_port_status_html(html(value))['LAN1']
        assert port.speed_mbps==speed and port.raw_status==value
    assert parse_lan_port_status_html(html('Down'))['LAN1'].link=='DOWN'


def test_lan_option_is_not_actual_link():
    port=parse_lan_port_status_html(html('Up, 2.5Gb, Full'))['LAN1']
    assert port.speed_mbps == 2500


def test_fxs_and_lan_results():
    dev={'model':'GRG-4361','firmware':'MTA-1.0.14','mac':'3872C0112255','wan':[{'Interface':n,'VLAN ID':v,'Connection Type':t,'Protocol':p} for n,v,t,p in [('nas0_0','7','TR069','IPoE'),('nas0_1','747','VOICE','IPoE'),('nas0_2','9','Other','Bridged')]]}
    pon={'ONU State':'O5','Tx Power':'7.0 dBm','Temperature':'35 C','Voltage':'3 V','Rx Power':'-10 dBm','Bias Current':'10 mA'}
    scans={'sn':'26C4361XXXF-AA000006','mac':'3872C0112255','gpon':'CMTDC0112255'}
    lan=parse_lan_port_status_html(html('Up, 10Gb, Full'))
    overall,rows=assess(dev,'CMTDC0112255',pon,scans,'MTA-1.0.14',lan_status=lan,phone_led='PASS')
    r={x['item']:x for x in rows}
    assert r['FXS']['result']=='PASS' and r['LAN1 Link Speed']['result']=='PASS'
    _,rows=assess(dev,'CMTDC0112255',pon,scans,'MTA-1.0.14',lan_status=parse_lan_port_status_html(html('Up, 2.5Gb, Full')),phone_led='FAIL')
    r={x['item']:x for x in rows}
    assert r['FXS']['result']=='FAIL' and r['LAN1 Link Speed']['result']=='FAIL'


def test_master_lan_fxs_columns(tmp_path):
    from main import save_record
    from master_record import sync_master, HEADERS, MASTER_NAME
    from openpyxl import load_workbook
    root=tmp_path/'Records';run=root/'test_lan_fxs';run.mkdir(parents=True)
    rows=[{'item':'LAN1 Link Speed','expected':'Up, 10Gb, Full','actual':'Up, 10Gb, Full','result':'PASS'},
          {'item':'FXS','expected':'Phone LED green blinking','actual':'Operator: PASS','result':'PASS'}]
    details={'lan1':{'link':'UP','speed_mbps':10000,'duplex':'FULL','raw_status':'Up, 10Gb, Full'},'phone_led':'PASS','device':{},'pon':{}}
    save_record(run,'PASS',rows,details,'26C4361XXXF-AA000006','Tester',{})
    assert sync_master(root)==1
    wb=load_workbook(root/MASTER_NAME)
    headers=[cell.value for cell in wb['All Tests'][1]]
    assert headers==HEADERS
    data=dict(zip(headers,[cell.value for cell in wb['All Tests'][2]]))
    assert data['LAN1 Link Speed']=='PASS' and data['LAN1 Speed (Mbps)']==10000
    assert data['LAN1 Duplex']=='FULL' and data['FXS Result']=='PASS'
