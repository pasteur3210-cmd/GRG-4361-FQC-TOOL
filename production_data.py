"""Validated, immutable production-lot snapshots for FQC. No secrets or test limits in TXT."""
from __future__ import annotations
import configparser
import datetime as dt
import hashlib
import ipaddress
import json
import re
from pathlib import Path

ACTIVE_FILE = 'active_production.json'
REQUIRED = {
    'GENERAL': ('MODEL','CUSTOMER','CUSTOMER_PO','PRODUCTION_MO','BOM_PN','PRODUCTION_QTY'),
    'DEVICE': ('ROUTER_IP','APPROVED_FW'),
    'SN_RANGE': ('SN_START','SN_END'),
    'MAC_RANGE': ('MAC_START','MAC_END','MAC_QUANTITY'),
    'TEST_PROFILE': ('PROFILE_NAME','PROFILE_VERSION'),
}
ALL_KEYS = {s:set(keys) for s,keys in REQUIRED.items()}

def parse_production_text(text: str) -> dict:
    cp=configparser.ConfigParser(interpolation=None,strict=True)
    cp.optionxform=str
    try: cp.read_string(text)
    except configparser.Error as exc: raise ValueError('Invalid production TXT: '+str(exc)) from exc
    if set(cp.sections()) != set(REQUIRED):raise ValueError('Unexpected or missing TXT sections')
    for sec,keys in REQUIRED.items():
        if set(cp[sec].keys())!=ALL_KEYS[sec]:raise ValueError(f'{sec}: missing/unexpected/incorrect-case keys')
    d={s:{k:cp[s][k].strip() for k in keys} for s,keys in REQUIRED.items()}
    for sec,keys in REQUIRED.items():
        for k in keys:
            if not d[sec][k]:raise ValueError(f'{sec}.{k} cannot be blank')
    if d['GENERAL']['MODEL']!='GRG-4361':raise ValueError('MODEL must be GRG-4361')
    for key in ('CUSTOMER','CUSTOMER_PO','PRODUCTION_MO','BOM_PN'):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,79}',d['GENERAL'][key]):raise ValueError('Invalid '+key)
    qty=d['GENERAL']['PRODUCTION_QTY']
    if not qty.isdecimal() or int(qty)<1:raise ValueError('PRODUCTION_QTY must be positive integer')
    try:ipaddress.IPv4Address(d['DEVICE']['ROUTER_IP'])
    except ipaddress.AddressValueError as exc:raise ValueError('Invalid ROUTER_IP') from exc
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,64}',d['DEVICE']['APPROVED_FW']):raise ValueError('Invalid APPROVED_FW')
    from range_check import validate_config,normalize_mac
    r={'sn_start':d['SN_RANGE']['SN_START'],'sn_end':d['SN_RANGE']['SN_END'],
       'mac_start':d['MAC_RANGE']['MAC_START'],'mac_end':d['MAC_RANGE']['MAC_END'],
       'mac_quantity':d['MAC_RANGE']['MAC_QUANTITY']}
    validate_config(r)
    if int(r['mac_quantity'])!=4:raise ValueError('GRG-4361 requires MAC_QUANTITY=4')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,64}',d['TEST_PROFILE']['PROFILE_NAME']):raise ValueError('Invalid PROFILE_NAME')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,32}',d['TEST_PROFILE']['PROFILE_VERSION']):raise ValueError('Invalid PROFILE_VERSION')
    # This is an allocation-capacity warning, NOT a proof of MAC allocation step.
    available=int(normalize_mac(r['mac_end']),16)-int(normalize_mac(r['mac_start']),16)+1
    if available < int(qty)*4:raise ValueError('MAC range cannot accommodate production quantity at 4 MAC per DUT')
    return d

def import_and_activate(text: str, root:Path, source_name:str='production.txt', operator:str='') -> dict:
    d=parse_production_text(text)
    raw=text.encode('utf-8');digest=hashlib.sha256(raw).hexdigest()
    at=dt.datetime.now().astimezone().isoformat(timespec='seconds')
    info={'format_version':'1.0','source_file':Path(source_name).name,'sha256':digest,'import_time':at,
          'activated_by':operator,'lot_id':d['GENERAL']['PRODUCTION_MO'],'settings':d,'source':'TXT'}
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    snapshots=root/'Production_Snapshots';snapshots.mkdir(exist_ok=True)
    dest=snapshots/(digest+'.txt')
    if not dest.exists():dest.write_bytes(raw)
    # Atomic replacement: invalid import never replaces active lot.
    temp=root/(ACTIVE_FILE+'.tmp');temp.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(root/ACTIVE_FILE)
    return info

def active_production(root:Path) -> dict|None:
    path=Path(root)/ACTIVE_FILE
    if not path.is_file():return None
    obj=json.loads(path.read_text(encoding='utf-8'))
    d=obj.get('settings')
    if not isinstance(d,dict):raise ValueError('Invalid active production settings')
    parse_production_text(to_txt(d))
    return obj

def to_txt(data:dict) -> str:
    out=['# GRG-4361 Production Data V1.0 - no passwords or test limit overrides']
    for s,keys in REQUIRED.items():
        out.extend(['',f'[{s}]'])
        out.extend(f'{k}={data[s][k]}' for k in keys)
    return '\n'.join(out)+'\n'

def range_values(info:dict) -> dict:
    d=info['settings'];return {'sn_start':d['SN_RANGE']['SN_START'],'sn_end':d['SN_RANGE']['SN_END'],
      'mac_start':d['MAC_RANGE']['MAC_START'],'mac_end':d['MAC_RANGE']['MAC_END'],
      'mac_quantity':d['MAC_RANGE']['MAC_QUANTITY']}
