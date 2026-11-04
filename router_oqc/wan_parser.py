from __future__ import annotations

from dataclasses import dataclass, asdict
from html import unescape
import re


@dataclass
class WanEntry:
    interface: str
    vlan_id: str
    connection_type: str
    protocol: str
    ip_address: str = ""
    gateway: str = ""
    status: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class WanParseError(ValueError):
    pass


def _clean(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def _find_wan_table(html: str) -> str:
    marker = re.search(r"<h3>\s*WAN(?:&nbsp;|\s)*Configuration\s*</h3>", html, flags=re.I)
    if not marker:
        raise WanParseError("找不到 WAN Configuration 標題")
    start = marker.end()
    table = re.search(r"<table\b[^>]*>(.*?)</table>", html[start:], flags=re.I | re.S)
    if not table:
        raise WanParseError("找不到 WAN Configuration 表格")
    return table.group(1)


def parse_wan_entries(html: str) -> list[dict[str, str]]:
    table_html = _find_wan_table(html)

    # The device HTML sometimes omits <tr> start tags. Reading all <td> cells
    # and rebuilding fixed groups of seven is more reliable than row-only parsing.
    cells = [_clean(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", table_html, flags=re.I | re.S)]
    if len(cells) < 7:
        raise WanParseError(f"WAN 欄位不足：只找到 {len(cells)} 個資料欄")

    remainder = len(cells) % 7
    if remainder:
        raise WanParseError(f"WAN 欄位數不是 7 的倍數：count={len(cells)}, remainder={remainder}")

    entries: list[WanEntry] = []
    for idx in range(0, len(cells), 7):
        group = cells[idx:idx + 7]
        if not any(group):
            continue
        entry = WanEntry(
            interface=group[0],
            vlan_id=group[1],
            connection_type=group[2],
            protocol=group[3],
            ip_address=group[4],
            gateway=group[5],
            status=group[6].lower(),
        )
        if not entry.interface:
            raise WanParseError(f"WAN 第 {idx // 7 + 1} 筆缺少 Interface")
        entries.append(entry)

    if not entries:
        raise WanParseError("WAN Configuration 沒有資料")
    if len({x.interface for x in entries}) != len(entries):
        raise WanParseError("WAN Configuration 出現重複 Interface")

    return [x.to_dict() for x in entries]
