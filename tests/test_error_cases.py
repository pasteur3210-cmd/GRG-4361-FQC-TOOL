import pytest
from grg4361 import parse_gpon,parse_pon,parse_device

def test_gpon_missing():
    with pytest.raises(ValueError): parse_gpon('<html></html>')
def test_pon_missing():
    with pytest.raises(ValueError): parse_pon('<html></html>')
def test_device_missing():
    with pytest.raises(ValueError): parse_device('<html><body>Device Login</body></html>')
