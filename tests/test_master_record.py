import json
from pathlib import Path
from unittest.mock import patch
import pytest
from openpyxl import load_workbook
from master_record import sync_master, MASTER_NAME

def make_run(root, name, sn, overall='FAIL'):
    d=root/name;d.mkdir(parents=True)
    data={
        'timestamp':'2026-11-05T09:30:00+08:00','dut_sn':sn,'operator':'QA-01',
        'overall':overall,'results':[{'item':'GPON SN vs MAC','expected':'CMTD0CFFC101',
              'actual':'CMTD000BCD6C','result':'FAIL' if overall=='FAIL' else 'PASS'}],
        'details':{'device':{'model':'GRG-4361','mac':'64680CFFC101','firmware':'MTA-1.0.14',
              'wan':[{'Interface':'nas0_0','VLAN ID':'7','Connection Type':'TR069','Protocol':'IPoE','Status':'down'}]},
              'gpon':'CMTD000BCD6C','pon':{'ONU State':'O1','Temperature':'35 C'}}}
    (d/'result.json').write_text(json.dumps(data),encoding='utf-8')
    return d

def test_multi_unit_append_and_retest(tmp_path):
    make_run(tmp_path,'20261105_090000_000001','SN001','FAIL')
    assert sync_master(tmp_path)==1
    make_run(tmp_path,'20261105_090100_000001','SN002','PASS')
    make_run(tmp_path,'20261105_090200_000001','SN001','PASS')
    assert sync_master(tmp_path)==2
    assert sync_master(tmp_path)==0
    wb=load_workbook(tmp_path/MASTER_NAME)
    ws=wb['All Tests']
    assert ws.max_row==4
    assert [ws.cell(i,4).value for i in (2,3,4)]==['SN001','SN002','SN001']
    assert [ws.cell(i,5).value for i in (2,3,4)]==[1,1,2]
    assert [ws.cell(i,24).value for i in (2,3,4)]==['FAIL','PASS','PASS']
    assert ws['F2'].value=='64680CFFC101'
    assert ws['K2'].value=='Missing'
    assert wb['Summary']['B2'].value == 3
    assert wb['Summary']['B3'].value == 2
    assert wb['Summary']['B4'].value == 1

def test_open_workbook_failure_preserves_journal(tmp_path):
    run=make_run(tmp_path,'20261105_090000_000001','SN001')
    with patch('master_record.os.replace',side_effect=PermissionError('Excel file locked')):
        with pytest.raises(PermissionError):sync_master(tmp_path)
    assert (run/'result.json').exists()
    assert not (tmp_path/MASTER_NAME).exists()
    assert sync_master(tmp_path)==1
    assert sync_master(tmp_path)==0

def test_existing_master_preserved_if_locked(tmp_path):
    make_run(tmp_path,'r001','SN001');sync_master(tmp_path)
    make_run(tmp_path,'r002','SN002')
    with patch('master_record.os.replace',side_effect=PermissionError('Workbook open')):
        with pytest.raises(PermissionError):sync_master(tmp_path)
    assert load_workbook(tmp_path/MASTER_NAME)['All Tests'].max_row==2
    assert sync_master(tmp_path)==1

def test_bad_journal_not_appended(tmp_path):
    bad=tmp_path/'broken';bad.mkdir();(bad/'result.json').write_text('{broken',encoding='utf8')
    assert sync_master(tmp_path)==0
    assert load_workbook(tmp_path/MASTER_NAME)['All Tests'].max_row==1
