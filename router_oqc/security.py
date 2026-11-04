from __future__ import annotations

import base64
from urllib.parse import quote


def encode_password(password: str) -> str:
    """Match login.asp encode64(password), using UTF-8 Base64."""
    return base64.b64encode(password.encode("utf-8")).decode("ascii")


def js_encode_component(value: str) -> str:
    """
    Match the encoding adjustments used by common.js postTableEncrypt().
    JavaScript encodeURIComponent leaves ! ' ( ) ~ unescaped, but the router
    code explicitly escapes those five characters and converts %20 to +.
    """
    encoded = quote(value, safe="-_.!~*'()")
    replacements = {
        "!": "%21",
        "'": "%27",
        "(": "%28",
        ")": "%29",
        "~": "%7E",
        "%20": "+",
    }
    for old, new in replacements.items():
        encoded = encoded.replace(old, new)
    return encoded


def build_login_checksum_input(username: str, encoded_password: str) -> str:
    """
    Preserve the exact form order observed in login.asp:
    username, password(disabled/skipped), remember(unchecked/skipped),
    encodePassword, save(clicked submit), submit-url.
    """
    return (
        f"username={js_encode_component(username)}&"
        f"encodePassword={js_encode_component(encoded_password)}&"
        "save=Log+In&"
        "submit-url=%2Fadmin%2Flogin.asp&"
    )


def _to_int32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def calculate_post_security_flag(input_value: str) -> int:
    """Python port of common.js postTableEncrypt checksum algorithm."""
    csum = 0
    i = 0
    length = len(input_value)

    while i < length:
        if i + 4 > length:
            if i < length:
                csum = _to_int32(csum + (ord(input_value[i]) << 24))
            if i + 1 < length:
                csum = _to_int32(csum + (ord(input_value[i + 1]) << 16))
            if i + 2 < length:
                csum = _to_int32(csum + (ord(input_value[i + 2]) << 8))
            break

        block = (
            (ord(input_value[i]) << 24)
            + (ord(input_value[i + 1]) << 16)
            + (ord(input_value[i + 2]) << 8)
            + ord(input_value[i + 3])
        )
        csum = _to_int32(csum + block)
        i += 4

    csum = _to_int32((csum & 0xFFFF) + (csum >> 16))
    csum &= 0xFFFF
    return (~csum) & 0xFFFF


def create_login_values(username: str, password: str) -> tuple[str, int]:
    encoded = encode_password(password)
    checksum_input = build_login_checksum_input(username, encoded)
    return encoded, calculate_post_security_flag(checksum_input)
