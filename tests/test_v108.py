from main import App

def row(item, actual, expected, result):
    return {'item': item, 'actual': actual, 'expected': expected, 'result': result}

def test_single_failure_banner_shows_value_not_path():
    s=App.format_status('FAIL', [row('PON Tx Power','5.599545 dBm','6.8 to 7.2 dBm','FAIL')])
    assert s == 'FQC FAIL | PON Tx Power: 5.599545 dBm | Spec: 6.8 to 7.2 dBm'
    assert 'Records' not in s

def test_multiple_failures_shows_count():
    s=App.format_status('FAIL', [row('Tx','5','6','FAIL'),row('BID','19','20','FAIL')])
    assert '2 Failed Items' in s

def test_pass_and_review():
    assert 'All Required Checks Passed' in App.format_status('PASS', [row('Model','OK','OK','PASS')])
    assert 'SN Range' in App.format_status('REVIEW',[row('SN Range','none','range','REVIEW')])

def test_error_and_pending_master():
    assert 'ConnectionError' in App.format_status('ConnectionError: timeout',[],'error')
    assert 'All Required' in App.format_status('PASS | MASTER PENDING',[])
