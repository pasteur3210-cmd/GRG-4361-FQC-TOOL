from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urljoin
from .wan_config_parser import parse_wan_config_page,WanConfig
from .post_security import post_security_flag
from .client import RouterClient,RouterError

BRIDGE_FIELDS=[
('v6TunnelRv4IP',''),('lkname','0'),('vlan','ON'),('vid','160'),('vprio','1'),('multicast_vid','160'),('adslConnectionMode','0'),('brmode','3'),('chEnable','1'),('ctype','2'),('ctypeForBridge','2'),('mtu','2000'),('mtu_pppoe','1492'),('maccloneaddr',''),('IpProtocolType','3'),('auth','0'),('acName',''),('serviceName',''),('dnsMode','0'),('dns1',''),('dns2',''),('opt60_val',''),('iaid','0'),('duid_type','1'),('duid_ent_num','0'),('duid_id',''),('manufacturer',''),('product_class',''),('model_name',''),('serial_num',''),('v6TunnelType','0'),('SixrdMode','0'),('SixrdBRv4IP',''),('SixrdIPv4MaskLen',''),('SixrdPrefix',''),('SixrdPrefixLen',''),('Ipv6Dns16rd',''),('Ipv6Dns26rd',''),('Ipv6Addr6in4',''),('Ipv6PrefixLen6in4',''),('Ipv6Gateway6in4',''),('v6TunnelRv4IP6in4',''),('dnsV6Mode6in4','1'),('Ipv6Dns16in4',''),('Ipv6Dns26in4',''),('v6TunnelRv4IP6to4',''),('Ipv6Dns16to4',''),('Ipv6Dns26to4',''),('AddrMode','1'),('Ipv6Addr',''),('Ipv6PrefixLen',''),('Ipv6Gateway',''),('iapd','ON'),('dnsV6Mode','1'),('napt_v6','0'),('s4over6Type','0'),('dslite_aftr_hostname',''),('submit-url','/admin/multi_wan_generic.asp'),('lst','ppp0_nas0_0'),('encodePppUserName',''),('encodePppPassword',''),('qosEnabled','ON'),('apply','Apply Changes'),('itfGroup','0')]

@dataclass
class ApplyResult:
    response_text:str; security_flag:int; payload:list[tuple[str,str]]

def read_wan(client:RouterClient):
    r=client._get('admin/multi_wan_generic.asp',allow_redirects=True,headers={'Referer':client.base_url})
    if r.status_code!=200 or 'Device Login' in r.text: raise RouterError('WAN_CONFIG_READ_FAILED',f'WAN設定頁 HTTP {r.status_code}')
    configs,token=parse_wan_config_page(r.text)
    return configs,token,r.text

def apply_bridge_vlan160(client:RouterClient,csrf_token:str)->ApplyResult:
    fields=list(BRIDGE_FIELDS)
    flag=post_security_flag(fields)
    payload=fields+[('postSecurityFlag',str(flag)),('csrftoken',csrf_token)]
    r=client._post('boaform/admin/formWanEth',data=dict(payload),allow_redirects=True,headers={'Referer':urljoin(client.base_url,'admin/multi_wan_generic.asp')})
    if r.status_code!=200: raise RouterError('WAN_APPLY_HTTP_ERROR',f'Apply HTTP {r.status_code}')
    if 'Change setting successfully' not in r.text: raise RouterError('WAN_APPLY_RESPONSE_FAIL','Router未回傳設定成功訊息')
    return ApplyResult(r.text,flag,payload)
