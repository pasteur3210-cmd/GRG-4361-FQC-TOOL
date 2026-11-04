from __future__ import annotations

from dataclasses import asdict, dataclass
import ast
import re


class OmciParseError(ValueError):
    pass


@dataclass
class OmciInformation:
    vendor_id: str = ""
    software_version_1: str = ""
    software_version_2: str = ""
    equipment_id: str = ""
    hardware_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def complete(self) -> bool:
        return all([
            self.vendor_id,
            self.software_version_1,
            self.software_version_2,
            self.equipment_id,
            self.hardware_version,
        ])

    @property
    def missing_fields(self) -> list[str]:
        values = {
            "OMCI Vendor ID": self.vendor_id,
            "OMCI Software Version 1": self.software_version_1,
            "OMCI Software Version 2": self.software_version_2,
            "OMCI Equipment ID": self.equipment_id,
            "HW Version": self.hardware_version,
        }
        return [name for name, value in values.items() if not value]


_VARIABLES = {
    "vendor_id": "omci_vendor_id_value",
    "software_version_1": "omci_sw_ver1_value",
    "software_version_2": "omci_sw_ver2_value",
    "equipment_id": "omci_eqid_value",
    "hardware_version": "cwmp_hw_ver_value",
}


def _decode_js_string(raw: str) -> str:
    raw = raw.strip()
    try:
        return str(ast.literal_eval(raw)).strip()
    except (ValueError, SyntaxError):
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            return raw[1:-1].strip()
        return raw.strip()


def _extract_variable(html: str, variable_name: str) -> str:
    pattern = re.compile(
        rf"\bvar\s+{re.escape(variable_name)}\s*=\s*(?P<value>'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")\s*;",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(html)
    return _decode_js_string(match.group("value")) if match else ""


def parse_omci_information_html(html: str, strict: bool = True) -> OmciInformation:
    info = OmciInformation(**{
        field: _extract_variable(html, variable)
        for field, variable in _VARIABLES.items()
    })
    if strict and not info.complete:
        raise OmciParseError("OMCI欄位缺失：" + ", ".join(info.missing_fields))
    return info
