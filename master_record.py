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
    'Overall Result','Failure Items','Review Items','Record Path', 'Label MAC','Label GPON SN','LED Initial','LED Functional','Tx Power Result','PON BID','BID Length Result','BID Pattern Result','Production MO','Customer PO','BOM P/N','Customer','Production Qty','Router IP','Production Data ID','Production File SHA-256','Test Profile Version','Station ID','SN Start','SN End','MAC Start','MAC End','MAC Quantity'
]

def _make_book():
    wb=Workbook();ws=wb.active;ws.title='All Tests';ws.append(HEADERS)
    ws.freeze_panes='D2';ws.auto_filter.ref=f'A1:{get_column_letter(len(HEADERS))}1'
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
        payload.get('overall',''),failures('FAIL'),failures('REVIEW'),str(run_dir),
        payload.get('label_scans',{}).get('mac',''),payload.get('label_scans',{}).get('gpon',''),
        results.get('LED Initial',{}).get('result',''),results.get('LED Functional',{}).get('result',''),
        results.get('PON Tx Power',{}).get('result',''),
        details.get('bid',''),results.get('PON BID Length',{}).get('result',''),results.get('PON BID Pattern',{}).get('result',''),
        *production_columns(payload)
    ]

def production_columns(payload):
    p=payload.get('production_data') or (payload.get('details') or {}).get('production_data')
    if not p:return ['']*15
    d=p.get('settings',{});g=d.get('GENERAL',{});v=d.get('DEVICE',{});t=d.get('TEST_PROFILE',{})
    return [g.get('PRODUCTION_MO',''),g.get('CUSTOMER_PO',''),g.get('BOM_PN',''),g.get('CUSTOMER',''),
            g.get('PRODUCTION_QTY',''),v.get('ROUTER_IP',''),p.get('lot_id',''),p.get('sha256',''),t.get('PROFILE_VERSION',''),'',d.get('SN_RANGE',{}).get('SN_START',''),d.get('SN_RANGE',{}).get('SN_END',''),d.get('MAC_RANGE',{}).get('MAC_START',''),d.get('MAC_RANGE',{}).get('MAC_END',''),d.get('MAC_RANGE',{}).get('MAC_QUANTITY','')]

def update_production_sheets(wb,ws):
    headers=list(next(ws.iter_rows(min_row=1,max_row=1,values_only=True)))
    idx={str(x):i for i,x in enumerate(headers)}
    lots={};lot_examples={}
    for row in ws.iter_rows(min_row=2,values_only=True):
        def get(k):return row[idx[k]] if k in idx and idx[k]<len(row) else ''
        mo=get('Production MO')
        if mo:
            digest=get('Production File SHA-256') or ''
            key=(mo,digest)
            if key not in lots:lots[key]={'mo':mo,'po':get('Customer PO'),'bom':get('BOM P/N'),'customer':get('Customer'),
              'qty':get('Production Qty'),'ip':get('Router IP'),'hash':digest,'profile':get('Test Profile Version'),'first':get('Test Time (ISO 8601)'),'tests':0,'sn_start':get('SN Start'),'sn_end':get('SN End'),'mac_start':get('MAC Start'),'mac_end':get('MAC End'),'mac_qty':get('MAC Quantity')}
            lots[key]['tests']+=1
            lot_examples[key]=get('Test ID')
    current=wb['Production Info'] if 'Production Info' in wb else wb.create_sheet('Production Info')
    current.delete_rows(1,current.max_row);current.append(['Production lots in Master','Count'])
    current.append(['Distinct Lot Snapshots',len(lots)])
    for p in lots.values():
        current.append([p['mo']+' / '+p['bom'],p['tests']])
        for label,key in [('Customer PO','po'),('BOM P/N','bom'),('Customer','customer'),('Production Quantity','qty'),('Router IP','ip'),('Profile Version','profile'),('File SHA-256','hash'),('SN Start','sn_start'),('SN End','sn_end'),('MAC Start','mac_start'),('MAC End','mac_end'),('MAC Quantity','mac_qty')]:
            current.append([label,p[key]])
    hist=wb['Lot History'] if 'Lot History' in wb else wb.create_sheet('Lot History')
    hist.delete_rows(1,hist.max_row)
    hist.append(['Production MO','Customer PO','BOM P/N','Customer','Production Quantity','Router IP','Profile Version','File SHA-256','First Test Time','Test Attempts'])
    for p in lots.values():hist.append([p[k] for k in ('mo','po','bom','customer','qty','ip','profile','hash','first','tests')])
    for key,p in lots.items():
        current.append(['LOT RANGE DETAILS: '+p['mo'],''])
        # Historical range values are preserved in each run's result.json; references in All Tests identify that run.
        current.append(['Source Run ID',lot_examples[key]])
    for sheet in (current,hist):
        sheet.freeze_panes='A2'
        for cell in sheet[1]:cell.font=Font(bold=True,color='FFFFFF');cell.fill=PatternFill('solid',fgColor='17365D')
        for col in range(1,sheet.max_column+1):sheet.column_dimensions[get_column_letter(col)].width=30 if col!=8 else 68
    # Write numeric summary values to avoid empty formula caches in non-Excel viewers.
    summary=wb['Summary'] if 'Summary' in wb else wb.create_sheet('Summary')
    outcomes=[str(row[idx['Overall Result']] or '') for row in ws.iter_rows(min_row=2,values_only=True)]
    for n,(label,value) in enumerate([('Total Test Attempts',len(outcomes))]+[(k,outcomes.count(k)) for k in ('PASS','FAIL','REVIEW','ERROR')],2):
        summary.cell(n,1,label);summary.cell(n,2,value)

def sync_master(root: Path, timeout=3):
    """Rebuild/append missing runs. Idempotent via immutable run ID; preserve pending on lock/error."""
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    master=root/MASTER_NAME
    lock=FileLock(str(master)+'.lock',timeout=timeout)
    with lock:
        wb=load_workbook(master) if master.exists() else _make_book()
        ws=wb['All Tests']
        # Compatible upgrade for existing V1.0.3 Master workbook.
        for i,header in enumerate(HEADERS,1):
            if ws.cell(1,i).value != header: ws.cell(1,i,header)
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
        ws.auto_filter.ref=f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
        update_production_sheets(wb,ws)
        temp=None
        try:
            with NamedTemporaryFile(dir=root,prefix='.fqc_master_',suffix='.xlsx',delete=False) as f:
                temp=Path(f.name)
            wb.save(temp)
            os.replace(temp,master)  # Excel-open/permission failure leaves original workbook intact.
        finally:
            if temp is not None and temp.exists():temp.unlink()
        return added
