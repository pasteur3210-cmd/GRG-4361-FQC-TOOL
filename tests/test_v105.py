from grg4361 import Inspector, assess, parse_device
from test_grg4361 import device_html


def sample_pon(state, tx='No signal'):
    return {'Temperature':'38 C','Voltage':'3.3 V','Tx Power':tx,'Rx Power':'No signal','Bias Current':'0 mA','ONU State':state}


def test_o5_timeout_results_in_fail_but_tx_is_skipped():
    device=parse_device(device_html())
    overall, rows=assess(device,'CMTD0CFFC101',sample_pon('O1'),{'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'},'MTA-1.0.14')
    assert overall == 'FAIL'
    assert next(r for r in rows if r['item']=='O5 Timeout')['result']=='FAIL'
    assert next(r for r in rows if r['item']=='PON Tx Power')['result']=='SKIP'


def test_o5_success_has_no_timeout_and_checks_tx():
    device=parse_device(device_html())
    overall, rows=assess(device,'CMTD0CFFC101',sample_pon('O5','7.0 dBm'),{'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'},'MTA-1.0.14')
    assert not any(r['item']=='O5 Timeout' for r in rows)
    assert next(r for r in rows if r['item']=='PON Tx Power')['result']=='PASS'


def test_defaults_and_polls_stop_at_deadline(monkeypatch):
    import grg4361
    clock=[0.0]
    class Dummy:
        debug=None
        def login(self,*args): pass
    obj=Inspector.__new__(Inspector)
    obj.client=Dummy()
    requested=[]
    def read(path):
        requested.append(path)
        if path=='status.asp': return device_html()
        if path=='gpon.asp': return '<tr><th>Serial Number</th><td>CMTD0CFFC101</td></tr>'
        return '<table>'+''.join(f'<tr><th>{key}</th><td>{val}</td></tr>' for key,val in sample_pon('O1').items())+'</table>'
    def fake_sleep(seconds): clock[0]+=seconds
    monkeypatch.setattr(grg4361.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(grg4361.time,'sleep',fake_sleep)
    obj.read=read
    overall,rows,details=obj.run('root','secret',{'sn':'12345678901234567890','mac':'64680CFFC101','gpon':'CMTD0CFFC101'},'MTA-1.0.14')
    assert clock[0] == 10
    assert requested.count('status_pon.asp')==11  # at seconds 0..10 inclusive
    assert details['o5_timeout_seconds']==10
    assert details['o5_timeout'] is True
    assert overall=='FAIL'
