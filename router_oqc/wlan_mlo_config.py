from __future__ import annotations

from dataclasses import asdict, dataclass
import base64
import re

from bs4 import BeautifulSoup

from .security import calculate_post_security_flag, js_encode_component


class WlanMloConfigError(ValueError):
    pass


@dataclass
class WlanMloSnapshot:
    ssid: str
    channel_5g: int
    band_5g: int
    channel_width_5g: int
    txpower_5g: int
    band_2g: int
    channel_width_2g: int
    channel_2g: int
    txpower_2g: int
    wlan_idx: int
    band2g5g_support: int
    wlan_band_select: int
    dfs_enable: int
    csrftoken: str
    wlan_enable: str = "ON"
    mode: int = 0
    repeater_ssid: str = "repeater_ssid4"

    def to_dict(self) -> dict:
        return asdict(self)


def _js_int(html: str, name: str, required: bool = True, default: int = 0) -> int:
    patterns = [
        rf"\bvar\s+{re.escape(name)}\s*=\s*(-?\d+)\s*;?",
        rf"\b{name}\s*=\s*(-?\d+)\s*;?",
        rf"document\.wlanSetup\.{re.escape(name)}\.value\s*=\s*(-?\d+)\s*;?",
    ]
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return int(match.group(1))
    if required:
        raise WlanMloConfigError(f"找不到 {name}")
    return default


def _js_string(html: str, name: str) -> str:
    match = re.search(
        rf'\bvar\s+{re.escape(name)}\s*=\s*["\'](.*?)["\']\s*;',
        html,
        flags=re.S,
    )
    if not match:
        raise WlanMloConfigError(f"找不到 {name}")
    return match.group(1)


def _assigned_value(html: str, field: str, default: int | None = None) -> int:
    match = re.search(
        rf"document\.wlanSetup\.{re.escape(field)}\.value\s*=\s*(-?\d+)\s*;",
        html,
    )
    if match:
        return int(match.group(1))
    if default is not None:
        return default
    raise WlanMloConfigError(f"找不到 {field} 設定值")


def _selected_index_value(html: str, field: str, default: int = 0) -> int:
    # Current firmware maps tx power index 0 to payload value 0 (100%).
    match = re.search(
        rf"document\.wlanSetup\.{re.escape(field)}\.selectedIndex\s*=\s*(\d+)\s*;",
        html,
    )
    return int(match.group(1)) if match else default


def parse_wlan_mlo_snapshot(html: str) -> WlanMloSnapshot:
    if "WLAN Basic Settings" not in html or "formWlanMloSetup" not in html:
        raise WlanMloConfigError("WLAN Basic Settings 頁面特徵不存在")

    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", attrs={"action": re.compile(r"formWlanMloSetup")})
    if form is None:
        raise WlanMloConfigError("找不到 formWlanMloSetup")

    csrf = form.find("input", attrs={"name": "csrftoken"})
    token = (csrf.get("value", "") if csrf else "").strip()
    if not token:
        raise WlanMloConfigError("csrftoken 缺失")

    repeater = form.find("input", attrs={"name": "repeaterSSID"})
    repeater_ssid = repeater.get("value", "repeater_ssid4") if repeater else "repeater_ssid4"

    return WlanMloSnapshot(
        ssid=_js_string(html, "ssid_5g"),
        channel_5g=_js_int(html, "defaultChan_5g"),
        band_5g=_js_int(html, "defaultBand_5g"),
        channel_width_5g=_assigned_value(html, "chanwid_5g"),
        txpower_5g=_selected_index_value(html, "txpower_5g", 0),
        band_2g=_js_int(html, "defaultBand_2g"),
        channel_width_2g=_assigned_value(html, "chanwid_2g"),
        channel_2g=_js_int(html, "defaultChan_2g"),
        txpower_2g=_selected_index_value(html, "txpower_2g", 0),
        wlan_idx=_js_int(html, "wlan_idx"),
        band2g5g_support=_js_int(html, "Band2G5GSupport"),
        wlan_band_select=_js_int(html, "wlanBand2G5GSelect", required=False, default=0),
        dfs_enable=_js_int(html, "dfs_enable"),
        csrftoken=token,
        repeater_ssid=repeater_ssid,
    )


def _checksum_input(pairs: list[tuple[str, str]]) -> str:
    return "".join(
        f"{name}={js_encode_component(value)}&"
        for name, value in pairs
        if name not in {"postSecurityFlag", "csrftoken"}
    )


def build_channel36_payload(snapshot: WlanMloSnapshot) -> dict[str, str]:
    # Exact order and values validated against the user's captured Edge payload.
    # Only chan_5g changes. Other settings are reconstructed from the current page.
    encoded_ssid = base64.b64encode(snapshot.ssid.encode("utf-8")).decode("ascii")

    pairs = [
        ("wlanEnable", snapshot.wlan_enable),
        ("mode", str(snapshot.mode)),
        ("band_5g", str(snapshot.band_5g)),
        ("chanwid_5g", str(snapshot.channel_width_5g)),
        ("chan_5g", "36"),
        ("txpower_5g", str(snapshot.txpower_5g)),
        ("band_2g", str(snapshot.band_2g)),
        ("chanwid_2g", str(snapshot.channel_width_2g)),
        ("chan_2g", str(snapshot.channel_2g)),
        ("txpower_2g", str(snapshot.txpower_2g)),
        ("repeaterSSID", snapshot.repeater_ssid),
        ("submit-url", "/admin/wlmlobasic.asp"),
        ("save", "Apply Changes"),
        ("basicrates_6g", "0"),
        ("operrates_6g", "0"),
        ("basicrates_5g", "496"),
        ("operrates_5g", "4080"),
        ("basicrates_2g", "15"),
        ("operrates_2g", "4095"),
        ("wlan_idx", str(snapshot.wlan_idx)),
        ("Band2G5GSupport", str(snapshot.band2g5g_support)),
        ("wlanBand2G5GSelect", str(snapshot.wlan_band_select)),
        ("dfs_enable", str(snapshot.dfs_enable)),
        ("encodessid", encoded_ssid),
        ("encoderepeaterSSID", ""),
    ]

    flag = calculate_post_security_flag(_checksum_input(pairs))
    pairs.extend([
        ("postSecurityFlag", str(flag)),
        ("csrftoken", snapshot.csrftoken),
    ])
    return dict(pairs)


PROTECTED_FIELDS = (
    "ssid",
    "band_5g",
    "channel_width_5g",
    "txpower_5g",
    "band_2g",
    "channel_width_2g",
    "channel_2g",
    "txpower_2g",
    "wlan_idx",
    "band2g5g_support",
    "wlan_band_select",
    "dfs_enable",
)


def compare_side_effects(before: WlanMloSnapshot, after: WlanMloSnapshot) -> dict[str, dict]:
    changes: dict[str, dict] = {}
    for field in PROTECTED_FIELDS:
        old = getattr(before, field)
        new = getattr(after, field)
        if old != new:
            changes[field] = {"before": old, "after": new}
    return changes
