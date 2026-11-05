"""Approved SN/MAC range and MAC allocation validation (read-only)."""
import json
import re
from pathlib import Path

CONFIG_NAME='production_range.json'

def normalize_mac(value):
    return re.sub(r'[:-]', '', str(value).strip()).upper()

def load_range(path):
    path=Path(path)
    if not path.is_file():return None
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Invalid range configuration')
    validate_config(data)
    return data

def validate_config(config):
    first=str(config['sn_start']).strip();last=str(config['sn_end']).strip()
    if len(first)!=20 or len(last)!=20 or first>last:
        raise ValueError('SN range must contain ordered 20-character SNs')
    # Equal prefix and fixed width numeric suffix prevent lexicographic mistakes.
    ma=re.fullmatch(r'(.*?)(\d+)',first);mb=re.fullmatch(r'(.*?)(\d+)',last)
    if not ma or not mb or ma.group(1)!=mb.group(1) or len(ma.group(2))!=len(mb.group(2)):
        raise ValueError('SN start/end must share a prefix and numeric suffix width')
    low=normalize_mac(config['mac_start']);high=normalize_mac(config['mac_end'])
    if not re.fullmatch(r'[0-9A-F]{12}',low) or not re.fullmatch(r'[0-9A-F]{12}',high) or int(low,16)>int(high,16):
        raise ValueError('Invalid MAC start/end')
    qty=int(config['mac_quantity'])
    if qty<1 or qty>256:raise ValueError('Invalid MAC quantity')
    return True

def check_sn(sn,config):
    if not config:return 'REVIEW'
    first=str(config['sn_start']);last=str(config['sn_end']);sn=str(sn).strip()
    prefix=re.fullmatch(r'(.*?)(\d+)',first).group(1)
    if len(sn)!=20 or not sn.startswith(prefix):return 'FAIL'
    suffix=sn[len(prefix):]
    if not suffix.isdigit() or len(suffix)!=len(first)-len(prefix):return 'FAIL'
    return 'PASS' if first<=sn<=last else 'FAIL'

def check_mac(mac,config):
    if not config:return 'REVIEW'
    value=normalize_mac(mac)
    if not re.fullmatch(r'[0-9A-F]{12}',value):return 'FAIL'
    low=int(normalize_mac(config['mac_start']),16);high=int(normalize_mac(config['mac_end']),16)
    base=int(value,16);qty=int(config['mac_quantity'])
    # Base MAC + quantity is a provisional sequential allocation model.
    return 'PASS' if low<=base and base+qty-1<=high else 'FAIL'

def check_duplicate(root,sn,mac):
    """Historical identity collision detection; matching SN+MAC is a legitimate retest."""
    root=Path(root);mac=normalize_mac(mac)
    for path in root.glob('*/result.json'):
        try:rec=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):continue
        old_sn=str(rec.get('dut_sn','')).strip();scans=rec.get('label_scans') or {}
        old_mac=normalize_mac(scans.get('mac',''))
        if old_sn==sn and old_mac and old_mac!=mac:return 'FAIL'
        if old_sn and old_sn!=sn and old_mac==mac:return 'FAIL'
    return 'PASS'
