from __future__ import annotations

import base64
import hashlib
import re


class WirelessParseError(ValueError):
    pass


def _js_string(html: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1\s*;",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(2) if match else ""


def parse_wlan_basic_html(html: str) -> dict[str, str]:
    ssid_2g = _js_string(html, "ssid_2g")
    ssid_5g = _js_string(html, "ssid_5g")

    if not ssid_2g and not ssid_5g:
        match = re.search(
            r"<input\b[^>]*\bname\s*=\s*['\"]?ssid['\"]?[^>]*\bvalue\s*=\s*(['\"])(.*?)\1",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            ssid_2g = ssid_5g = match.group(2)

    if not ssid_2g and not ssid_5g:
        raise WirelessParseError("wlmlobasic.asp 中找不到 SSID")

    shared = bool(ssid_2g and ssid_5g and ssid_2g == ssid_5g)
    return {
        "SSID 2.4G": ssid_2g,
        "SSID 5G": ssid_5g,
        "SSID": ssid_2g or ssid_5g,
        "SSID Mode": "MLO_SHARED" if shared else "SEPARATE",
    }


def parse_wpa_html(html: str) -> dict[str, str]:
    match = re.search(
        r"_wpaPSK\s*\[\s*0\s*\]\s*=\s*(['\"])(.*?)\1\s*;",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise WirelessParseError("wlwpa.asp 中找不到 _wpaPSK[0]")

    encoded = match.group(2).strip()
    try:
        key_bytes = base64.b64decode(encoded, validate=True)
        key = key_bytes.decode("utf-8")
    except Exception as exc:
        raise WirelessParseError("WPA Key Base64 解碼失敗") from exc

    encrypt_match = re.search(r"_encrypt\s*\[\s*0\s*\]\s*=\s*(\d+)\s*;", html)
    encrypt_code = encrypt_match.group(1) if encrypt_match else ""
    encrypt_name = {
        "6": "WPA2 Mixed",
        "16": "WPA3",
        "20": "WPA3 Transition",
        "64": "Enhanced Open Transition",
    }.get(encrypt_code, encrypt_code)

    return {
        "WPA Key": key,
        "WPA Key Length": str(len(key)),
        "WPA Key SHA256": hashlib.sha256(key.encode("utf-8")).hexdigest(),
        "Encryption": encrypt_name,
    }


def parse_wireless_pages(basic_html: str, security_html: str) -> dict[str, str]:
    data = parse_wlan_basic_html(basic_html)
    data.update(parse_wpa_html(security_html))
    return data
