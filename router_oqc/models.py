from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DeviceStatus:
    system: dict[str, str] = field(default_factory=dict)
    lan: dict[str, str] = field(default_factory=dict)
    wan: list[dict[str, str]] = field(default_factory=list)
    pon_status: object | None = None
    wireless: dict[str, str] = field(default_factory=dict)
    raw_url: str = ""

    def get(self, section: str, key: str, default: str = "") -> str:
        sources = {
            "system": self.system,
            "lan": self.lan,
            "wireless": self.wireless,
        }
        return sources.get(section, {}).get(key, default)

    def to_dict(self) -> dict[str, Any]:
        wireless_safe = dict(self.wireless)
        if wireless_safe.get("WPA Key"):
            wireless_safe["WPA Key"] = "********"
        if wireless_safe.get("WPA Key SHA256"):
            wireless_safe["WPA Key SHA256"] = wireless_safe["WPA Key SHA256"][:12]
        return {
            "system": self.system,
            "lan": self.lan,
            "wan": self.wan,
            "pon_status": self.pon_status.to_dict() if hasattr(self.pon_status, "to_dict") else {},
            "wireless": wireless_safe,
            "raw_url": self.raw_url,
        }
