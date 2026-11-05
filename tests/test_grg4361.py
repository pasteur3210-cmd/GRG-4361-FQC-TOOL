from grg4361 import parse_device,parse_gpon,parse_pon,assess

def device_html():
    return '''<table><tr><th>Device Name</th><td>GRG-4361</td></tr><tr><th>Firmware Version</th><td>MTA-1.0.14</td></tr><tr><th>MAC Address</th><td>64680cffc101</td></tr></table><p>WAN&nbsp;Configuration</p><table><tr><th>Interface</th><th>VLAN ID</th><th>Connection Type</th><th>Protocol</th><th>IP Address</th><th>Gateway</th><th>Status</th></tr><tr><td>nas0_0</td><td>7</td><td>TR069</td><td>IPoE</td><td></td><td></td><td>down</td></tr><tr><td>nas0_1</td><td>747</td><td>VOICE</td><td>IPoE</td><td></td><td></td><td>down</td></tr><tr><td>nas0_2</td><td>9</td><td>Other</td><td>Bridged</td><td></td><td></td><td>down</td></tr></table>'''
def pon_html():
    return '<table>'+''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k,v in [('Temperature','35.453125 C'),('Voltage','3.304700 V'),('Tx Power','No signal'),('Rx Power','No signal'),('Bias Current','0.000000 mA'),('ONU State','O1'),('ONU ID','0'),('LOID Status','Initial Status')])+'</table>'
def test_parse_device():
    d=parse_device(device_html());assert d['mac']=='64680CFFC101';assert len(d['wan'])==3

def test_gpon_whitespace():
    assert parse_gpon('<tr><th>Serial Number:</th><td>&nbsp;&nbsp;CMTD000BCD6C</td></tr>')=='CMTD000BCD6C'
def test_pon_no_signal():
    assert parse_pon(pon_html())['Tx Power']=='No signal'
def test_expected_fail():
    d=parse_device(device_html());overall,rows=assess(d,'CMTD000BCD6C',parse_pon(pon_html()))
    assert overall=='FAIL';assert next(x for x in rows if x['item']=='GPON SN vs MAC')['result']=='FAIL'
def test_valid_gpon_but_missing_fw():
    d=parse_device(device_html());overall,_=assess(d,'CMTD0CFFC101',parse_pon(pon_html()))
    assert overall=='FAIL'  # V1.0.4: O1, no scans and No signal must not pass
def test_valid_gpon_approved_fw_still_sn_review():
    d=parse_device(device_html());overall,_=assess(d,'CMTD0CFFC101',parse_pon(pon_html()),expected_firmware='MTA-1.0.14')
    assert overall=='FAIL'  # V1.0.4: O1, no scans and No signal must not pass


def test_malformed_wan_middle_row_is_not_lost():
    # Real DUT response: the nas0_1 row lacks an opening <tr> after nas0_0.
    html=device_html().replace('</tr><tr><td>nas0_1', '</tr><td>nas0_1')
    data=parse_device(html)
    assert [r['Interface'] for r in data['wan']]==['nas0_0','nas0_1','nas0_2']
    overall, rows=assess(data,'CMTD0CFFC101',parse_pon(pon_html()),expected_firmware='MTA-1.0.14')
    assert next(x for x in rows if x['item']=='WAN nas0_1')['result']=='PASS'

def test_wan_missing_is_still_fail():
    html=device_html().replace('<tr><td>nas0_1</td><td>747</td><td>VOICE</td><td>IPoE</td><td></td><td></td><td>down</td></tr>','')
    data=parse_device(html)
    _, rows=assess(data,'CMTD0CFFC101',parse_pon(pon_html()))
    assert next(x for x in rows if x['item']=='WAN nas0_1')['result']=='FAIL'
