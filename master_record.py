"""Append-only factory FQC master workbook with recoverable per-run journals."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from filelock import FileLock, Timeout

MASTER_NAME = 'GRG-4361_FQC_Master_Record.xlsx'
HEADERS = [
    'Test ID','Test Time (ISO 8601)','Operator','DUT SN','Retest No.','MAC','GPON SN',
    'Firmware','Model','WAN nas0_0','WAN nas0_1','WAN nas0_2',
    'WAN Link nas0_0','WAN Link nas0_1','WAN Link nas0_2',
    'PON Temperature','PON Voltage','PON Tx Power','PON Rx Power',
    'PON Bias Current','PON ONU State','PON ONU ID','PON LOID Status',
    'Overall Result','Failure Items','Review Items','Record Path'
]

def _make_book():
    wb=Workbook();ws=wb.active;ws.title='All Tests';ws.append(HEADERS)
    ws.freeze_panes='D2';ws.auto_filter.ref=f'A1:AA1'
    for idx,header in enumerate(HEADERS,1):
        cell=ws.cell(1,idx);cell.font=Font(color='FFFFFF',bold=True)
        cell.fill=PatternFill('solid',fgColor='17365D');cell.alignment=Alignment(wrap_text=True)
        ws.column_dimensions[get_column_letter(idx)].width=min(37,max(15,len(header)+3))
    ws.row_dimensions[1].height=32
    summary=wb.create_sheet('Summary')
    summary.append(['GRG-4361 FQC Master Record','Count'])
    for cell in summary[1]:
        cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D')
    for metric,formula in [
        ('Total Test Attempts',"=COUNTA('All Tests'!A:A)-1"),
        ('PASS',"=COUNTIF('All Tests'!X:X,\"PASS\")"),
        ('FAIL',"=COUNTIF('All Tests'!X:X,\"FAIL\")"),
        ('REVIEW',"=COUNTIF('All Tests'!X:X,\"REVIEW\")"),
        ('ERROR',"=COUNTIF('All Tests'!X:X,\"ERROR\")"),
    ]: summary.append([metric,formula])
    summary.column_dimensions['A'].width=40;summary.column_dimensions['B'].width=20
    summary['A9']='Each test attempt is retained. Retests do not overwrite original results.'
    return wb

def _row(payload, run_dir, number):
    results={r['item']:r for r in payload.get('results',[])}
    details=payload.get('details',{})
    device=details.get('device',{});pon=details.get('pon',{})
    wan={x.get('Interface'):x for x in device.get('wan',[])}
    def wan_value(name):
        x=wan.get(name)
        return ' | '.join(str(x.get(k,'')) for k in ('VLAN ID','Connection Type','Protocol')) if x else 'Missing'
    def wan_link(name):return str(wan.get(name,{}).get('Status',''))
    def failures(kind):return ', '.join(r['item'] for r in payload.get('results',[]) if r['result']==kind)
    return [
        run_dir.name,payload.get('timestamp',''),payload.get('operator',''),payload.get('dut_sn',''),number,
        device.get('mac',''),details.get('gpon',''),device.get('firmware',''),device.get('model',''),
        *[wan_value(n) for n in ('nas0_0','nas0_1','nas0_2')],
        *[wan_link(n) for n in ('nas0_0','nas0_1','nas0_2')],
        *[pon.get(k,'') for k in ('Temperature','Voltage','Tx Power','Rx Power','Bias Current','ONU State','ONU ID','LOID Status')],
        payload.get('overall',''),failures('FAIL'),failures('REVIEW'),str(run_dir)
    ]

def sync_master(root: Path, timeout=3):
    """Rebuild/append missing runs. Idempotent via immutable run ID; preserve pending on lock/error."""
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    master=root/MASTER_NAME
    lock=FileLock(str(master)+'.lock',timeout=timeout)
    with lock:
        wb=load_workbook(master) if master.exists() else _make_book()
        ws=wb['All Tests']
        existing={str(ws.cell(i,1).value) for i in range(2,ws.max_row+1)}
        counts={}
        for i in range(2,ws.max_row+1):
            sn=str(ws.cell(i,4).value or '')
            if sn:counts[sn]=counts.get(sn,0)+1
        added=0
        for run_dir in sorted(root.iterdir()):
            path=run_dir/'result.json'
            if not run_dir.is_dir() or not path.is_file() or run_dir.name in existing:continue
            try:
                payload=json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(payload.get('results'),list) or not payload.get('overall'):continue
                sn=str(payload.get('dut_sn',''))
                number=counts.get(sn,0)+1 if sn else 0
                ws.append(_row(payload,run_dir,number))
                if sn:counts[sn]=number
                existing.add(run_dir.name);added+=1
            except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError):
                continue  # An incomplete per-run journal is not a valid Master Record entry.
        if not added and master.exists():return 0
        ws.auto_filter.ref=f'A1:AA{ws.max_row}'
        temp=None
        try:
            with NamedTemporaryFile(dir=root,prefix='.fqc_master_',suffix='.xlsx',delete=False) as f:
                temp=Path(f.name)
            wb.save(temp)
            os.replace(temp,master)  # Excel-open/permission failure leaves original workbook intact.
        finally:
            if temp is not None and temp.exists():temp.unlink()
        return added
