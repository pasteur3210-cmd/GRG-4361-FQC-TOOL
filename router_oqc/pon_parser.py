from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from bs4 import BeautifulSoup


class PonParseError(ValueError):
    pass


@dataclass
class PonStatus:
    temperature: float | None = None
    voltage: float | None = None
    tx_power: float | None = None
    rx_power: float | None = None
    bias_current: float | None = None
    onu_state: str = ""
    tx_power_raw: str = ""
    rx_power_raw: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def format_number(value: float | None, unit: str = "") -> str:
        if value is None:
            return ""
        suffix = f" {unit}" if unit else ""
        return f"{value:.2f}{suffix}"

    @property
    def temperature_display(self) -> str:
        return self.format_number(self.temperature, "°C")

    @property
    def voltage_display(self) -> str:
        return self.format_number(self.voltage, "V")

    @property
    def tx_power_display(self) -> str:
        return self.format_number(self.tx_power, "dBm") if self.tx_power is not None else self.tx_power_raw

    @property
    def rx_power_display(self) -> str:
        return self.format_number(self.rx_power, "dBm") if self.rx_power is not None else self.rx_power_raw

    @property
    def bias_current_display(self) -> str:
        return self.format_number(self.bias_current, "mA")


def _extract_number(value: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value or "")
    return float(match.group(0)) if match else None


def parse_pon_status_html(html: str) -> PonStatus:
    soup = BeautifulSoup(html, "html.parser")
    values: dict[str, str] = {}

    # Use TH -> next TD lookup. The router HTML contains a missing </tr> after Tx Power.
    for th in soup.find_all("th"):
        key = " ".join(th.get_text(" ", strip=True).split())
        td = th.find_next("td")
        if key and td:
            values[key] = " ".join(td.get_text(" ", strip=True).split())

    required = ("Temperature", "Voltage", "Tx Power", "Rx Power", "Bias Current", "ONU State")
    missing = [key for key in required if key not in values]
    if missing:
        raise PonParseError("PON欄位缺失：" + ", ".join(missing))

    return PonStatus(
        temperature=_extract_number(values["Temperature"]),
        voltage=_extract_number(values["Voltage"]),
        tx_power=_extract_number(values["Tx Power"]),
        rx_power=_extract_number(values["Rx Power"]),
        bias_current=_extract_number(values["Bias Current"]),
        onu_state=values["ONU State"].strip(),
        tx_power_raw=values["Tx Power"].strip(),
        rx_power_raw=values["Rx Power"].strip(),
    )
