from pathlib import Path
import json
from range_check import validate_config,check_sn,check_mac,check_duplicate
from grg4361 import assess

C={'sn_start':'26C4361XXXF-AA000001','sn_end':'26C4361XXXF-AA000999','mac_start':'3872C0112200','mac_end':'3872C01122FF','mac_quantity':4}

def test_sn_range():
    assert validate_config(C)
    assert check_sn('26C4361XXXF-AA000006',C)=='PASS'
    assert check_sn('26C4361XXXF-AA001000',C)=='FAIL'
    assert check_sn('26C4361XXXF-AA000006',None)=='REVIEW'

def test_mac_allocation():
    assert check_mac('38:72:C0:11:22:55',C)=='PASS'
    assert check_mac('3872C01122FD',C)=='FAIL'
    assert check_mac('3872C0112255',None)=='REVIEW'

def test_duplicates_and_retests(tmp_path):
    p=tmp_path/'r1';p.mkdir()
    (p/'result.json').write_text(json.dumps({'dut_sn':'26C4361XXXF-AA000006','label_scans':{'mac':'3872C0112255'}}))
    assert check_duplicate(tmp_path,'26C4361XXXF-AA000006','3872C0112255')=='PASS'
    assert check_duplicate(tmp_path,'26C4361XXXF-AA000006','3872C0112256')=='FAIL'
    assert check_duplicate(tmp_path,'26C4361XXXF-AA000007','3872C0112255')=='FAIL'

def test_assessment_range_included():
    dev={'model':'GRG-4361','firmware':'MTA-1.0.14','mac':'3872C0112255','wan':[{'Interface':'nas0_0','VLAN ID':'7','Connection Type':'TR069','Protocol':'IPoE','Status':'up'},{'Interface':'nas0_1','VLAN ID':'747','Connection Type':'VOICE','Protocol':'IPoE','Status':'up'},{'Interface':'nas0_2','VLAN ID':'9','Connection Type':'Other','Protocol':'Bridged','Status':'up'}]}
    pon={'ONU State':'O5','Tx Power':'7.0 dBm'}
    status,rows=assess(dev,'CMTDC0112255',pon,{'sn':'26C4361XXXF-AA000006','mac':'38:72:C0:11:22:55','gpon':'CMTDC0112255'},'MTA-1.0.14',range_config=C,duplicate_result='PASS')
    assert status=='PASS'
    assert {r['item']:r['result'] for r in rows}['MAC Allocation Range']=='PASS'
