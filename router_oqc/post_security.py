from __future__ import annotations
from urllib.parse import quote

def encode_component(value: str) -> str:
    out=quote(str(value),safe="-_.!~*'()")
    return (out.replace('!','%21').replace("'",'%27').replace('(','%28')
            .replace(')','%29').replace('~','%7E').replace('%20','+'))

def form_string(fields: list[tuple[str,str]]) -> str:
    return ''.join(f"{name.replace('[','%5B').replace(']','%5D')}={encode_component(value)}&" for name,value in fields)

def post_security_flag(fields: list[tuple[str,str]]) -> int:
    data=form_string(fields)
    csum=0; i=0
    while i < len(data):
        if i+4 > len(data):
            if i < len(data): csum += ord(data[i])<<24
            if i+1 < len(data): csum += ord(data[i+1])<<16
            if i+2 < len(data): csum += ord(data[i+2])<<8
            break
        csum += (ord(data[i])<<24)+(ord(data[i+1])<<16)+(ord(data[i+2])<<8)+ord(data[i+3])
        i += 4
    csum=((csum & 0xffff)+(csum >> 16)) & 0xffff
    return (~csum) & 0xffff
