
from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Callable
from urllib.parse import urlencode, urljoin, urlsplit

import requests
import urllib3
from bs4 import BeautifulSoup

from .models import DeviceStatus
from .parser import parse_status_html
from .wireless_parser import parse_wireless_pages, WirelessParseError
from .pon_parser import parse_pon_status_html, PonParseError, PonStatus
from .omci_parser import parse_omci_information_html, OmciInformation
from .lan_port_parser import parse_lan_port_status_html, LanPortParseError, LanPortStatus
from .wlan_mlo_config import (
    WlanMloSnapshot,
    WlanMloConfigError,
    parse_wlan_mlo_snapshot,
    build_channel36_payload,
)
from .security import create_login_values

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RouterError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class LoginResult:
    final_url: str
    status_code: int


@dataclass
class LegacyResponse:
    status_code: int
    text: str
    content: bytes
    url: str
    headers: dict[str, str]


class RouterClient:
    """
    HTTP client for older Realtek/Boa router web servers.

    Some firmware returns an HTML body before a valid HTTP status line.
    Python requests/http.client raises BadStatusLine, while Edge still displays
    the page. This client first uses requests and then falls back to a raw
    HTTP-over-TLS request that accepts this legacy response format.
    """

    def __init__(
        self,
        host: str,
        protocol: str = "https",
        timeout: float = 10.0,
        verify_tls: bool = False,
        debug: Callable[[str], None] | None = None,
    ):
        host = host.strip().rstrip("/")
        if "://" in host:
            self.base_url = host + "/"
        else:
            self.base_url = f"{protocol}://{host}/"

        self.timeout = timeout
        self.verify_tls = verify_tls
        self.debug = debug or (lambda _: None)
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1",
        })

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def _is_bad_status_line(exc: BaseException) -> bool:
        text = repr(exc)
        return "BadStatusLine" in text or "ProtocolError" in text

    def _cookie_header(self) -> str:
        return "; ".join(f"{cookie.name}={cookie.value}" for cookie in self.session.cookies)

    def _store_set_cookie(self, headers: dict[str, str]) -> None:
        raw = headers.get("set-cookie", "")
        if not raw:
            return
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
            for name, morsel in cookie.items():
                self.session.cookies.set(name, morsel.value)
        except Exception:
            self.debug("Legacy response Set-Cookie parse failed")

    def _legacy_raw_request(
        self,
        method: str,
        url: str,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> LegacyResponse:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        host = parsed.hostname or ""
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        body = b""
        request_headers = dict(self.session.headers)
        request_headers.update(headers or {})
        request_headers["Host"] = host
        request_headers["Connection"] = "close"

        cookies = self._cookie_header()
        if cookies:
            request_headers["Cookie"] = cookies

        if data is not None:
            body = urlencode(data).encode("utf-8")
            request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            request_headers["Content-Length"] = str(len(body))

        lines = [f"{method} {path} HTTP/1.0"]
        for key, value in request_headers.items():
            lines.append(f"{key}: {value}")
        packet = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1") + body

        self.debug(f"LEGACY {method} {url}")
        sock = socket.create_connection((host, port), timeout=self.timeout)
        try:
            sock.settimeout(self.timeout)
            if scheme == "https":
                context = ssl.create_default_context()
                if not self.verify_tls:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=host)

            sock.sendall(packet)
            chunks: list[bytes] = []
            while True:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            try:
                sock.close()
            except Exception:
                pass

        raw = b"".join(chunks)
        if not raw:
            raise RouterError("EMPTY_RESPONSE", "Router沒有回傳資料")

        status_code = 200
        response_headers: dict[str, str] = {}
        content = raw

        if raw.startswith(b"HTTP/"):
            header_blob, sep, content = raw.partition(b"\r\n\r\n")
            if not sep:
                header_blob, sep, content = raw.partition(b"\n\n")
            header_lines = header_blob.decode("iso-8859-1", errors="replace").splitlines()
            if header_lines:
                parts = header_lines[0].split()
                if len(parts) >= 2 and parts[1].isdigit():
                    status_code = int(parts[1])
            for line in header_lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    response_headers[key.strip().lower()] = value.strip()
        else:
            # Legacy HTTP/0.9-style response: body starts directly with HTML.
            self.debug(
                "Legacy HTTP response accepted: missing HTTP status line; "
                f"first_bytes={raw[:80]!r}"
            )

        self._store_set_cookie(response_headers)
        encoding = "utf-8"
        content_type = response_headers.get("content-type", "")
        if "charset=" in content_type.lower():
            encoding = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
        try:
            text = content.decode(encoding, errors="replace")
        except LookupError:
            text = content.decode("utf-8", errors="replace")

        return LegacyResponse(
            status_code=status_code,
            text=text,
            content=content,
            url=url,
            headers=response_headers,
        )

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, str] | None = None,
        allow_redirects: bool = True,
        headers: dict[str, str] | None = None,
    ):
        url = urljoin(self.base_url, path)
        self.debug(f"{method} {url}")
        try:
            response = self.session.request(
                method,
                url,
                data=data,
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=allow_redirects,
                headers=headers,
            )
            self.debug(
                f"{method} status={response.status_code} final_url={response.url} "
                f"bytes={len(response.content)}"
            )
            return response
        except requests.Timeout as exc:
            raise RouterError("CONNECT_TIMEOUT", "連線逾時") from exc
        except requests.ConnectionError as exc:
            if self._is_bad_status_line(exc):
                self.debug("requests received BadStatusLine; switching to legacy transport")
                try:
                    response = self._legacy_raw_request(method, url, data=data, headers=headers)
                except (OSError, ssl.SSLError, RouterError) as legacy_exc:
                    raise RouterError(
                        "LEGACY_CONNECTION_FAILED",
                        f"Router回應格式異常，Legacy模式仍失敗：{legacy_exc}",
                    ) from legacy_exc

                # Follow one Location redirect when a valid header exists.
                location = response.headers.get("location")
                if allow_redirects and location and response.status_code in {301, 302, 303, 307, 308}:
                    next_method = "GET" if response.status_code in {301, 302, 303} else method
                    next_data = None if next_method == "GET" else data
                    return self._request(
                        next_method,
                        urljoin(url, location),
                        data=next_data,
                        allow_redirects=True,
                        headers=headers,
                    )
                return response
            raise RouterError("CONNECTION_FAILED", "無法連線至Router") from exc
        except requests.RequestException as exc:
            raise RouterError("HTTP_ERROR", str(exc)) from exc

    def _get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, data: dict[str, str], **kwargs):
        return self._request("POST", path, data=data, **kwargs)

    def get_login_page(self) -> tuple[str, str]:
        response = self._get("admin/login.asp", allow_redirects=True)
        if response.status_code != 200:
            raise RouterError("LOGIN_PAGE_HTTP_ERROR", f"登入頁HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", attrs={"name": "csrftoken"})
        if not token or not token.get("value"):
            raise RouterError("LOGIN_CSRF_NOT_FOUND", "找不到登入頁csrftoken")

        return response.text, str(token["value"])

    def login(self, username: str, password: str) -> LoginResult:
        _, csrf_token = self.get_login_page()
        encoded_password, security_flag = create_login_values(username, password)

        payload = {
            "username": username,
            "encodePassword": encoded_password,
            "save": "Log In",
            "submit-url": "/admin/login.asp",
            "postSecurityFlag": str(security_flag),
            "csrftoken": csrf_token,
        }

        response = self._post(
            "boaform/admin/formLogin",
            data=payload,
            allow_redirects=True,
            headers={"Referer": urljoin(self.base_url, "admin/login.asp")},
        )

        text = response.text.lower()
        if "device login" in text and "name=\"encodepassword\"" in text:
            raise RouterError("AUTHENTICATION_FAILED", "帳號或密碼錯誤")

        probe = self._get(
            f"status.asp?v={int(time.time() * 1000)}",
            allow_redirects=True,
            headers={"Referer": self.base_url},
        )
        probe_text = probe.text
        if (
            probe.status_code != 200
            or "Device Status" not in probe_text
            or "Device Name" not in probe_text
        ):
            if "Device Login" in probe_text:
                raise RouterError("AUTHENTICATION_FAILED", "登入後仍被導回登入頁")
            raise RouterError("SESSION_INVALID", "登入後無法存取Device Status")

        return LoginResult(final_url=response.url, status_code=response.status_code)

    def fetch_status(self) -> tuple[DeviceStatus, str]:
        url_path = f"status.asp?v={int(time.time() * 1000)}"
        response = self._get(
            url_path,
            allow_redirects=True,
            headers={"Referer": self.base_url},
        )
        if response.status_code != 200:
            raise RouterError("STATUS_PAGE_HTTP_ERROR", f"Status頁HTTP {response.status_code}")
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        try:
            status = parse_status_html(response.text, response.url)
        except ValueError as exc:
            raise RouterError("STATUS_PARSE_ERROR", str(exc)) from exc
        return status, response.text

    def fetch_wireless(self) -> tuple[dict[str, str], str, str]:
        basic = self._get(
            "admin/wlmlobasic.asp",
            allow_redirects=True,
            headers={"Referer": urljoin(self.base_url, "status.asp")},
        )
        if basic.status_code != 200 or "Device Login" in basic.text:
            raise RouterError(
                "WLAN_BASIC_HTTP_ERROR",
                f"WLAN Basic 頁面 HTTP {basic.status_code}",
            )

        security = self._get(
            "admin/wlwpa.asp",
            allow_redirects=True,
            headers={"Referer": urljoin(self.base_url, "admin/wlmlobasic.asp")},
        )
        if security.status_code != 200 or "Device Login" in security.text:
            raise RouterError(
                "WLAN_SECURITY_HTTP_ERROR",
                f"WLAN Security 頁面 HTTP {security.status_code}",
            )

        try:
            wireless = parse_wireless_pages(basic.text, security.text)
        except WirelessParseError as exc:
            raise RouterError("WIRELESS_PARSE_ERROR", str(exc)) from exc
        return wireless, basic.text, security.text





    def fetch_wlan_mlo_snapshot(self) -> tuple[WlanMloSnapshot, str]:
        response = self._get(
            "admin/wlmlobasic.asp",
            allow_redirects=True,
            headers={"Referer": urljoin(self.base_url, "status.asp")},
        )
        if response.status_code != 200:
            raise RouterError(
                "WLAN_BASIC_HTTP_ERROR",
                f"WLAN Basic 頁面 HTTP {response.status_code}",
            )
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        try:
            snapshot = parse_wlan_mlo_snapshot(response.text)
        except WlanMloConfigError as exc:
            raise RouterError("WLAN_MLO_PARSE_ERROR", str(exc)) from exc
        return snapshot, response.text

    def apply_wlan_channel36(
        self,
        snapshot: WlanMloSnapshot,
    ) -> tuple[str, dict[str, str]]:
        payload = build_channel36_payload(snapshot)
        response = self._post(
            "boaform/admin/formWlanMloSetup",
            data=payload,
            allow_redirects=False,
            headers={"Referer": urljoin(self.base_url, "admin/wlmlobasic.asp")},
        )
        if response.status_code not in {200, 302}:
            raise RouterError(
                "WLAN_APPLY_HTTP_ERROR",
                f"WLAN Apply HTTP {response.status_code}",
            )
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        if "Change setting successfully" not in response.text:
            raise RouterError(
                "WLAN_APPLY_RESPONSE_ERROR",
                "Router未回傳 Change setting successfully",
            )
        return response.text, payload

    def fetch_lan_port_status(self) -> tuple[dict[str, LanPortStatus], str]:
        response = self._get(
            f"lan_port_status.asp?v={int(time.time() * 1000)}",
            allow_redirects=True,
            headers={"Referer": self.base_url},
        )
        if response.status_code != 200:
            raise RouterError("LAN_PORT_HTTP_ERROR", f"LAN Port Status頁HTTP {response.status_code}")
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        try:
            statuses = parse_lan_port_status_html(response.text)
        except LanPortParseError as exc:
            raise RouterError("LAN_PORT_PARSE_ERROR", str(exc)) from exc
        return statuses, response.text

    def fetch_omci_information(self) -> tuple[OmciInformation, str]:
        response = self._get(
            f"omci_info.asp?v={int(time.time() * 1000)}",
            allow_redirects=True,
            headers={"Referer": self.base_url},
        )
        if response.status_code != 200:
            raise RouterError("OMCI_INFO_HTTP_ERROR", f"OMCI Information頁HTTP {response.status_code}")
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        information = parse_omci_information_html(response.text, strict=False)
        return information, response.text

    def fetch_pon_status(self) -> tuple[PonStatus, str]:
        response = self._get(
            f"status_pon.asp?v={int(time.time() * 1000)}",
            allow_redirects=True,
            headers={"Referer": self.base_url},
        )
        if response.status_code != 200:
            raise RouterError("PON_STATUS_HTTP_ERROR", f"PON Status頁HTTP {response.status_code}")
        if "Device Login" in response.text:
            raise RouterError("SESSION_EXPIRED", "Session已失效")
        try:
            status = parse_pon_status_html(response.text)
        except PonParseError as exc:
            raise RouterError("PON_STATUS_PARSE_ERROR", str(exc)) from exc
        return status, response.text

    def fetch_all(self) -> tuple[DeviceStatus, dict[str, str]]:
        status, status_html = self.fetch_status()
        wireless, basic_html, security_html = self.fetch_wireless()
        status.wireless.update(wireless)
        return status, {
            "status_page.html": status_html,
            "wlmlobasic.asp.html": basic_html,
            "wlwpa.asp.html": security_html,
        }

    def logout(self) -> None:
        try:
            self._get("admin/logout2.asp", allow_redirects=False)
        except Exception:
            pass
