from __future__ import annotations
from dataclasses import dataclass,asdict
import re
from bs4 import BeautifulSoup

@dataclass
class WanConfig:
    index:int; name:str; applicationtype:int; cmode:int; brmode:int; napt:int; vlan:int; vid:int; vprio:int; mVid:int; enable:int; mtu:int; mtu_pppoe:int; IpProtocol:int
    def to_dict(self): return asdict(self)
    @property
    def channel_mode(self): return {0:'Bridged',1:'IPoE',2:'PPPoE'}.get(self.cmode,str(self.cmode))
    @property
    def priority_display(self): return '' if self.vprio==0 else str(self.vprio-1)

def _ival(block,key,default=0):
    m=re.search(r'new it\("'+re.escape(key)+r'",\s*("(?:\\.|[^"])*"|-?\d+)\)',block)
    if not m:return default
    v=m.group(1)
    return v[1:-1] if v.startswith('"') else int(v)

def parse_wan_config_page(html:str)->tuple[list[WanConfig],str]:
    token=''
    soup=BeautifulSoup(html,'html.parser')
    el=soup.find('input',attrs={'name':'csrftoken'})
    if el: token=str(el.get('value',''))
    configs=[]
    cursor=0
    marker='new it_nr("'
    end_marker='new it("omci_configured", 0)))'
    while True:
        pos=html.find(marker,cursor)
        if pos<0: break
        name_start=pos+len(marker)
        name_end=html.find('"',name_start)
        if name_end<0: break
        name=html[name_start:name_end]
        end=html.find(end_marker,name_end)
        if end<0: break
        block=html[name_end:end+len(end_marker)]
        idx=len(configs)
        configs.append(WanConfig(idx,name,int(_ival(block,'applicationtype')),int(_ival(block,'cmode')),int(_ival(block,'brmode')),int(_ival(block,'napt')),int(_ival(block,'vlan')),int(_ival(block,'vid')),int(_ival(block,'vprio')),int(_ival(block,'mVid')),int(_ival(block,'enable')),int(_ival(block,'mtu')),int(_ival(block,'mtu_pppoe')),int(_ival(block,'IpProtocol'))))
        cursor=end+len(end_marker)
    if not configs: raise ValueError('找不到 WAN links[] 設定資料')
    if not token: raise ValueError('找不到 WAN 頁面 csrftoken')
    return configs,token
