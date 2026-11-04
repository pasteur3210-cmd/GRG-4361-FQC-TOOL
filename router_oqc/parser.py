from __future__ import annotations

from .wan_parser import parse_wan_entries, WanParseError

import re
from bs4 import BeautifulSoup

from .models import DeviceStatus


SYSTEM_KEYS = {
    "Device Name",
    "Serial Number",
    "Uptime",
    "Firmware Version",
    "WiFi Driver Version",
    "CPU Usage",
    "Memory Usage",
    "Name Servers",
    "IPv4 Default Gateway",
    "IPv6 Default Gateway",
}

LAN_KEYS = {
    "IP Address",
    "Subnet Mask",
    "DHCP Server",
    "MAC Address",
}

WAN_HEADERS = [
    "Interface",
    "VLAN ID",
    "Connection Type",
    "Protocol",
    "IP Address",
    "Gateway",
    "Status",
]


def clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        return value.strip().upper()
    return ":".join(compact[i:i+2] for i in range(0, 12, 2)).upper()


def _extract_key_value_rows(soup: BeautifulSoup) -> tuple[dict[str, str], dict[str, str]]:
    system: dict[str, str] = {}
    lan: dict[str, str] = {}

    for row in soup.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue

        key = clean_text(th.get_text(" ", strip=True))
        if not key:
            continue

        progress = td.find(attrs={"aria-valuenow": True})
        if progress and key in {"CPU Usage", "Memory Usage"}:
            value = f'{progress.get("aria-valuenow", "").strip()}%'
        else:
            value = clean_text(td.get_text(" ", strip=True))

        if key in SYSTEM_KEYS:
            system[key] = value
        elif key in LAN_KEYS:
            lan[key] = normalize_mac(value) if key == "MAC Address" else value

    return system, lan


def _extract_wan_by_rows(soup: BeautifulSoup) -> list[dict[str, str]]:
    for table in soup.find_all("table"):
        header_cells = [clean_text(x.get_text(" ", strip=True)) for x in table.find_all("th")]
        if not all(header in header_cells for header in WAN_HEADERS):
            continue

        records: list[dict[str, str]] = []
        for row in table.find_all("tr"):
            cells = [clean_text(td.get_text(" ", strip=True)) for td in row.find_all("td")]
            if len(cells) == 7:
                records.append(dict(zip(WAN_HEADERS, cells)))
        if records:
            return records
    return []


def _extract_wan_fallback(html: str) -> list[dict[str, str]]:
    """
    Router HTML may omit opening <tr> tags for alternating WAN rows.
    Extract the WAN table source and group sequential <td> cells in blocks of 7.
    """
    marker = "WAN&nbsp;Configuration"
    pos = html.find(marker)
    if pos < 0:
        marker = "WAN Configuration"
        pos = html.find(marker)
    if pos < 0:
        return []

    fragment = html[pos:]
    end = fragment.find("</table>")
    if end >= 0:
        fragment = fragment[:end + len("</table>")]

    soup = BeautifulSoup(fragment, "html.parser")
    cells = [clean_text(td.get_text(" ", strip=True)) for td in soup.find_all("td")]

    records: list[dict[str, str]] = []
    for index in range(0, len(cells), 7):
        chunk = cells[index:index + 7]
        if len(chunk) == 7 and chunk[0] and chunk[0] != "Interface":
            records.append(dict(zip(WAN_HEADERS, chunk)))
    return records


def parse_status_html(html: str, source_url: str = "") -> DeviceStatus:
    soup = BeautifulSoup(html, "html.parser")
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    body_text = clean_text(soup.get_text(" ", strip=True))

    if "Device Status" not in title and "Device Status" not in body_text:
        raise ValueError("STATUS_PAGE_SIGNATURE_NOT_FOUND")

    system, lan = _extract_key_value_rows(soup)
    wan = _extract_wan_by_rows(soup)

    fallback = _extract_wan_fallback(html)
    if len(fallback) > len(wan):
        wan = fallback

    try:
        wan = parse_wan_entries(html)
    except WanParseError:
        wan = []
    return DeviceStatus(system=system, lan=lan, wan=wan, raw_url=source_url)
