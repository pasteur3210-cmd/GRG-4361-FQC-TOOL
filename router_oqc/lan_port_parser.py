from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from bs4 import BeautifulSoup


class LanPortParseError(ValueError):
    pass


@dataclass
class LanPortStatus:
    port: str
    link: str = "DOWN"
    speed_mbps: int | None = None
    duplex: str = ""
    raw_status: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_port(value: str) -> str:
    text = " ".join(value.upper().split())
    match = re.search(r"\bLAN\s*([1-4])\b", text)
    if not match:
        raise LanPortParseError(f"無法辨識LAN名稱：{value}")
    return f"LAN{match.group(1)}"


def parse_lan_port_status_html(html: str) -> dict[str, LanPortStatus]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, LanPortStatus] = {}

    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 2:
            continue
        name_text = " ".join(cells[0].get_text(" ", strip=True).split())
        if not re.search(r"\bLAN\s*[1-4]\b", name_text, re.IGNORECASE):
            continue

        port = _normalize_port(name_text)
        raw = " ".join(cells[1].get_text(" ", strip=True).split())
        normalized = raw.upper().replace(" ", "")

        if "NOT-CONNECTED" in normalized or "NOTCONNECTED" in normalized:
            result[port] = LanPortStatus(port=port, link="DOWN", raw_status=raw)
            continue

        match = re.search(r"\bUP\s*,\s*(\d+(?:\.\d+)?)\s*(G(?:B|BPS)?|MB(?:PS)?)\s*,\s*(FULL|HALF)\b",raw,re.IGNORECASE)
        if not match:
            result[port] = LanPortStatus(port=port,link="DOWN" if re.search(r"\bDOWN\b",raw,re.I) else "UNKNOWN",raw_status=raw)
            continue
        magnitude=float(match.group(1));unit=match.group(2).upper()
        speed=round(magnitude*(1000 if unit.startswith('G') else 1))
        result[port]=LanPortStatus(port=port,link="UP",speed_mbps=speed,duplex=match.group(3).upper(),raw_status=raw)

    missing = ["LAN1"] if "LAN1" not in result else []
    if missing:
        raise LanPortParseError("LAN欄位缺失：" + ", ".join(missing))
    return result
