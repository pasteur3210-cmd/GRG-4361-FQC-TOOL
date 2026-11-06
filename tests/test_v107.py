from bid_telnet import extract_bid,assess_bid,BidTelnetError
from grg4361 import assess
from master_record import HEADERS, _row
from pathlib import Path
import pytest

def test_bid_good():
    bid=extract_bid('>labelinfo\r\nPON BID = B26C0000006_PPPNNNNN\r\nVersion = MTA\r\n>')
    assert bid=='B26C0000006_PPPNNNNN'
    assert len(bid)==20
    assert all(r['result']=='PASS' for r in assess_bid(bid))

def test_bid_invalid_length_and_pattern():
    rows=assess_bid('B26C00000006_PPPNNNNN')
    assert [r['result'] for r in rows]==['FAIL','PASS']
    rows=assess_bid('B26C0000006_AAANNNNN')
    assert [r['result'] for r in rows]==['PASS','FAIL']

def test_missing_bid():
    with pytest.raises(BidTelnetError):extract_bid('MAC = 3872C0112255')

def test_assess_removes_link_rows_and_adds_bid():
    d={'model':'GRG-4361','firmware':'MTA-1.0.14','mac':'3872C0112255',
       'wan':[{'Interface':n,'VLAN ID':v,'Connection Type':t,'Protocol':p,'Status':'down'} for n,v,t,p in [('nas0_0','7','TR069','IPoE'),('nas0_1','747','VOICE','IPoE'),('nas0_2','9','Other','Bridged')]]}
    pon={'ONU State':'O5','Tx Power':'7.0 dBm'}
    overall,rows=assess(d,'CMTDC0112255',pon,bid='B26C0000006_PPPNNNNN')
    assert not any(r['item'].startswith('WAN Link') for r in rows)
    assert len([r for r in rows if r['item'].startswith('WAN nas')])==3
    assert len([r for r in rows if r['item'].startswith('PON BID')])==2
    assert rows[-1]['item']!='WAN Link nas0_2'

def test_master_bid_columns():
    assert HEADERS[32:35]==['PON BID','BID Length Result','BID Pattern Result']
    p={'results':assess_bid('B26C0000006_PPPNNNNN'),'details':{'bid':'B26C0000006_PPPNNNNN'},'overall':'PASS'}
    row=_row(p,Path('/tmp/test_001'),1)
    assert len(row)==len(HEADERS)
    assert row[32:35]==['B26C0000006_PPPNNNNN','PASS','PASS']
