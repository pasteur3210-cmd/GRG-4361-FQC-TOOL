from pathlib import Path
from openpyxl import load_workbook
import pytest
from production_data import parse_production_text,import_and_activate,active_production,range_values
from master_record import sync_master,MASTER_NAME
import json

TEXT=(Path(__file__).parents[1]/'GRG-4361_Production_Data_TEMPLATE.txt').read_text()

def test_valid_template():
    d=parse_production_text(TEXT)
    assert d['GENERAL']['MODEL']=='GRG-4361'
    assert range_values({'settings':d})['mac_quantity']=='4'

@pytest.mark.parametrize('old,new',[
    ('MODEL=GRG-4361','MODEL=GRG-4297u'),
    ('APPROVED_FW=MTA-1.0.14','APPROVED_FW='),
    ('MAC_QUANTITY=4','MAC_QUANTITY=10'),
    ('ROUTER_IP=192.168.1.1','ROUTER_IP=wrong'),
    ('SN_END=26C4361XXXF-AA001000','SN_END=26C4361XXXF-AA000000'),
    ('PRODUCTION_QTY=1000','PRODUCTION_QTY=1000000'),
])
def test_invalid(old,new):
    with pytest.raises(ValueError):parse_production_text(TEXT.replace(old,new))

def test_bad_import_does_not_replace_active(tmp_path):
    info=import_and_activate(TEXT,tmp_path,'lot.txt','QA')
    with pytest.raises(ValueError):import_and_activate(TEXT.replace('MAC_QUANTITY=4','MAC_QUANTITY=5'),tmp_path,'bad.txt')
    assert active_production(tmp_path)['sha256']==info['sha256']
    assert (tmp_path/'Production_Snapshots'/(info['sha256']+'.txt')).is_file()

def test_master_lots_history_and_numeric_summary(tmp_path):
    info=import_and_activate(TEXT,tmp_path,'lot.txt')
    for n,res in enumerate(('FAIL','PASS')):
        directory=tmp_path/('RUN'+str(n));directory.mkdir()
        payload={'timestamp':'2026-11-06T12:00:00+08:00','dut_sn':'26C4361XXXF-AA000006',
          'overall':res,'results':[],'details':{'production_data':info},'production_data':info}
        (directory/'result.json').write_text(json.dumps(payload),encoding='utf-8')
    assert sync_master(tmp_path)==2
    wb=load_workbook(tmp_path/MASTER_NAME,data_only=True)
    assert wb['Summary']['B2'].value==2
    assert wb['Summary']['B3'].value==1
    assert wb['Summary']['B4'].value==1
    assert wb['Lot History']['A2'].value=='MO-EXAMPLE-001'
    assert wb['Lot History']['J2'].value==2
    assert wb['All Tests']['AJ2'].value=='MO-EXAMPLE-001'
    assert sync_master(tmp_path)==0
