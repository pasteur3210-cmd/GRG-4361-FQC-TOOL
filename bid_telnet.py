"""Minimal read-only Telnet labelinfo client, compatible with Python 3.11+."""
from __future__ import annotations
import re
import socket
import time

class BidTelnetError(RuntimeError):
    pass

def extract_bid(output: str) -> str:
    match=re.search(r'(?im)^\s*PON\s+BID\s*=\s*([^\r\n]+)',output)
    if not match:raise BidTelnetError('PON BID field missing from labelinfo')
    return match.group(1).strip()

def assess_bid(bid: str):
    bid=bid.strip()
    return [
       {'item':'PON BID Length','expected':'20 characters','actual':f'{len(bid)} | {bid}','result':'PASS' if len(bid)==20 else 'FAIL'},
       {'item':'PON BID Pattern','expected':'Contains consecutive PPP','actual':bid,'result':'PASS' if 'PPP' in bid else 'FAIL'},
    ]

def _strip_telnet(data: bytes, sock: socket.socket) -> bytes:
    """Remove complete Telnet command sequences and refuse offered options."""
    out=bytearray();i=0
    while i<len(data):
        if data[i]!=255:out.append(data[i]);i+=1;continue
        if i+1>=len(data):break
        cmd=data[i+1]
        if cmd==255:out.append(255);i+=2;continue
        if cmd in (251,252,253,254) and i+2<len(data):
            option=data[i+2]
            # WILL/WONT => DONT; DO/DONT => WONT
            sock.sendall(bytes([255,254 if cmd in (251,252) else 252,option]));i+=3;continue
        if cmd==250:
            end=data.find(b'\xff\xf0',i+2)
            if end<0:break
            i=end+2;continue
        i+=2
    return bytes(out)

def _read_until(sock,pattern,timeout):
    deadline=time.monotonic()+timeout;received=bytearray()
    while time.monotonic()<deadline:
        sock.settimeout(max(.05,deadline-time.monotonic()))
        try:chunk=sock.recv(4096)
        except socket.timeout:break
        if not chunk:break
        received.extend(_strip_telnet(chunk,sock))
        if re.search(pattern,received,re.I|re.M):return received.decode('utf-8',errors='replace')
    raise BidTelnetError('Telnet prompt/response timeout')

def read_bid(host:str,username:str,password:str,timeout:float=3.0)->str:
    """Authenticate and send only labelinfo; do not expose or persist credentials."""
    try:
        with socket.create_connection((host,23),timeout=timeout) as sock:
            _read_until(sock,rb'(?:login|username)\s*:',timeout)
            sock.sendall(username.encode('ascii')+b'\r\n')
            _read_until(sock,rb'password\s*:',timeout)
            sock.sendall(password.encode('utf-8')+b'\r\n')
            _read_until(sock,rb'(^|[\r\n])[^\r\n]*[>#$]\s*$',timeout)
            sock.sendall(b'labelinfo\r\n')
            response=_read_until(sock,rb'(^|[\r\n])[^\r\n]*[>#$]\s*$',timeout)
            return extract_bid(response)
    except BidTelnetError:raise
    except (OSError,UnicodeError) as exc:
        raise BidTelnetError('Telnet communication failed: '+type(exc).__name__) from exc
