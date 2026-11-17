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
    'Overall Result','Failure Items','Review Items','Record Path', 'Label MAC','Label GPON SN','LED Initial','LED Functional','Tx Power Result','PON BID','BID Length Result','BID Pattern Result','LAN1 Link Speed','LAN1 Speed (Mbps)','LAN1 Duplex','FXS Result'
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
        results.get('LAN1 Link Speed',{}).get('result',''),details.get('lan1',{}).get('speed_mbps',''),details.get('lan1',{}).get('duplex',''),results.get('FXS',{}).get('result','')
    ]

def production_columns(payload):
    p=payload.get('production_data') or (payload.get('details') or {}).get('production_data')
    if not p:return ['']*15
    d=p.get('settings',{});g=d.get('GENERAL',{});v=d.get('DEVICE',{});t=d.get('TEST_PROFILE',{})
    return [g.get('PRODUCTION_MO',''),g.get('CUSTOMER_PO',''),g.get('BOM_PN',''),g.get('CUSTOMER',''),
            g.get('PRODUCTION_QTY',''),v.get('ROUTER_IP',''),p.get('lot_id',''),p.get('sha256',''),t.get('PROFILE_VERSION',''),'',d.get('SN_RANGE',{}).get('SN_START',''),d.get('SN_RANGE',{}).get('SN_END',''),d.get('MAC_RANGE',{}).get('MAC_START',''),d.get('MAC_RANGE',{}).get('MAC_END',''),d.get('MAC_RANGE',{}).get('MAC_QUANTITY','')]

def update_production_sheets(wb, ws, root=None):
    """Keep production details in their own tabs rather than 15 mostly empty test columns."""
    lots = {}
    if root is not None:
        for run_dir in sorted(Path(root).iterdir()):
            source = run_dir / 'result.json'
            if not source.is_file():
                continue
            try:
                payload = json.loads(source.read_text(encoding='utf-8'))
                p = payload.get('production_data') or (payload.get('details') or {}).get('production_data')
                if not p:
                    continue
                d = p.get('settings') or {}
                g = d.get('GENERAL') or {}
                mo = g.get('PRODUCTION_MO', '')
                if not mo:
                    continue
                key = (mo, p.get('sha256', ''))
                if key not in lots:
                    lots[key] = dict(data=d, metadata=p, first=payload.get('timestamp', ''), count=0)
                lots[key]['count'] += 1
            except (OSError, ValueError, TypeError, AttributeError):
                continue
    current = wb['Production Info'] if 'Production Info' in wb else wb.create_sheet('Production Info')
    current.delete_rows(1, current.max_row)
    current.append(['Production Lot / Setting', 'Value'])
    current.append(['Distinct Lot Snapshots', len(lots)])
    hist = wb['Lot History'] if 'Lot History' in wb else wb.create_sheet('Lot History')
    hist.delete_rows(1, hist.max_row)
    hist.append(['Production MO', 'Customer PO', 'BOM P/N', 'Customer', 'Production Quantity', 'Router IP', 'Profile Version', 'File SHA-256', 'First Test Time', 'Test Attempts'])
    for (mo, sha), lot in lots.items():
        d = lot['data']; g=d.get('GENERAL') or {}; dev=d.get('DEVICE') or {}; profile=d.get('TEST_PROFILE') or {}
        current.append(['Production MO', mo])
        for group, keys in [('GENERAL', ('CUSTOMER','CUSTOMER_PO','PRODUCTION_MO','BOM_PN','PRODUCTION_QTY')),
                            ('DEVICE', ('ROUTER_IP','APPROVED_FW')),
                            ('SN_RANGE', ('SN_START','SN_END')),
                            ('MAC_RANGE', ('MAC_START','MAC_END','MAC_QUANTITY')),
                            ('TEST_PROFILE', ('PROFILE_NAME','PROFILE_VERSION'))]:
            for field in keys:
                current.append([group + '.' + field, (d.get(group) or {}).get(field, '')])
        current.append(['Production Data ID', lot['metadata'].get('lot_id','')])
        current.append(['SHA-256', sha])
        current.append(['Test Attempts', lot['count']])
        current.append(['', ''])
        hist.append([mo,g.get('CUSTOMER_PO',''),g.get('BOM_PN',''),g.get('CUSTOMER',''),g.get('PRODUCTION_QTY',''),dev.get('ROUTER_IP',''),profile.get('PROFILE_VERSION',''),sha,lot['first'],lot['count']])
    for sheet in (current, hist):
        sheet.freeze_panes = 'A2'
        for cell in sheet[1]:
            cell.font=Font(bold=True,color='FFFFFF')
            cell.fill=PatternFill('solid',fgColor='17365D')
        for col in range(1,sheet.max_column+1):
            sheet.column_dimensions[get_column_letter(col)].width=60 if sheet==current and col==1 else (68 if sheet==hist and col==8 else 30)
    summary=wb['Summary'] if 'Summary' in wb else wb.create_sheet('Summary')
    headers=list(next(ws.iter_rows(min_row=1,max_row=1,values_only=True)))
    ix=headers.index('Overall Result')
    outcomes=[str(row[ix] or '') for row in ws.iter_rows(min_row=2,values_only=True)]
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
        # Migrate old wide All Tests by header name; do not lose any test history.
        old_headers=[c.value for c in ws[1]]
        if old_headers != HEADERS:
            old_records=list(ws.iter_rows(min_row=2,values_only=True))
            old_index={header:i for i,header in enumerate(old_headers) if header is not None}
            ws.delete_rows(1,ws.max_row)
            ws.append(HEADERS)
            for old_row in old_records:
                if not any(v is not None for v in old_row):
                    continue
                ws.append([old_row[old_index[h]] if h in old_index and old_index[h]<len(old_row) else None for h in HEADERS])
            ws.auto_filter.ref=f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
            for col in range(1,max(len(old_headers),len(HEADERS))+1):
                letter=get_column_letter(col)
                ws.column_dimensions[letter].width=min(37,max(15,len(HEADERS[col-1])+3)) if col<=len(HEADERS) else 8

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
        if not added and master.exists() and old_headers == HEADERS:return 0
        ws.auto_filter.ref=f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
        update_production_sheets(wb,ws,root)
        temp=None
        try:
            with NamedTemporaryFile(dir=root,prefix='.fqc_master_',suffix='.xlsx',delete=False) as f:
                temp=Path(f.name)
            wb.save(temp)
            os.replace(temp,master)  # Excel-open/permission failure leaves original workbook intact.
        finally:
            if temp is not None and temp.exists():temp.unlink()
        return added
