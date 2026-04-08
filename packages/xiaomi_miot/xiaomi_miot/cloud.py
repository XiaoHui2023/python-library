import asyncio
import base64
import hashlib
import hmac
import json
import locale
import logging
import os
import random
import string
import time
from datetime import datetime, timezone
from urllib import parse

import aiohttp
import requests as _requests

from .rc4 import RC4

_LOGGER = logging.getLogger(__name__)

ACCOUNT_BASE = "https://account.xiaomi.com"
UA = "Android-7.1.1-1.0.0-ONEPLUS A3010-136-%s APP/xiaomi.smarthome APPV/62830"


class XiaomiCloudError(Exception):
    pass


class XiaomiLoginError(XiaomiCloudError):
    pass


def _gen_nonce() -> str:
    millis = int(round(time.time() * 1000))
    b = os.urandom(8) + (millis // 60000).to_bytes(4, "big")
    return base64.b64encode(b).decode()


def _signed_nonce(ssecurity: str, nonce: str) -> str:
    m = hashlib.sha256(base64.b64decode(ssecurity) + base64.b64decode(nonce))
    return base64.b64encode(m.digest()).decode()


def _json_decode(text: str) -> dict:
    try:
        return json.loads(text.replace("&&&START&&&", ""))
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _detect_timezone() -> str:
    try:
        offset = datetime.now(timezone.utc).astimezone().strftime("%z")
        return f"GMT{offset[:-2]}:{offset[-2:]}"
    except Exception:
        return "GMT+08:00"


class MiotCloud:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._external_session = session is not None
        self.session = session
        self.server: str = "cn"
        self.user_id: str | None = None
        self.service_token: str | None = None
        self.ssecurity: str | None = None
        self._client_id = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=16)
        )
        self._useragent = UA % self._client_id
        try:
            self._locale = locale.getlocale()[0] or "en_US"
        except Exception:
            self._locale = "en_US"
        self._timezone = _detect_timezone()

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session and not self._external_session:
            await self.session.close()
            self.session = None

    async def login(
        self, username: str, password: str, server: str = "cn"
    ) -> dict:
        self.server = server
        result = await asyncio.to_thread(
            self._login_sync, username, password
        )
        await self._ensure_session()
        return result

    def _login_sync(self, username: str, password: str) -> dict:
        """Synchronous login using requests (matches micloud library)."""
        sess = _requests.Session()
        sess.headers.update({"User-Agent": self._useragent})
        sess.cookies.update({
            "sdkVersion": "3.8.6",
            "deviceId": self._client_id,
            "userId": username,
        })

        # Step 1 — get login sign
        resp = sess.get(
            f"{ACCOUNT_BASE}/pass/serviceLogin?sid=xiaomiio&_json=true",
        )
        auth = _json_decode(resp.text)
        _LOGGER.debug("Step 1 code=%s keys=%s", auth.get("code"), list(auth.keys()))

        sign = auth.get("_sign", "")

        if auth.get("code") == 0:
            self.user_id = str(auth.get("userId", ""))
            self.ssecurity = auth.get("ssecurity")
            self.pass_token = auth.get("passToken")

        # If sign starts with http, it's already a location (skip Step 2)
        if sign.startswith("http"):
            location = sign
        else:
            # Step 2 — authenticate
            post_data = {
                "sid": "xiaomiio",
                "hash": hashlib.md5(password.encode()).hexdigest().upper(),
                "callback": "https://sts.api.io.mi.com/sts",
                "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
                "user": username,
                "_json": "true",
            }
            if sign:
                post_data["_sign"] = sign

            resp = sess.post(
                f"{ACCOUNT_BASE}/pass/serviceLoginAuth2",
                data=post_data,
            )
            auth2 = _json_decode(resp.text)
            _LOGGER.debug(
                "Step 2 code=%s result=%s keys=%s",
                auth2.get("code"), auth2.get("result"), list(auth2.keys()),
            )

            if auth2.get("result") != "ok":
                notify_url = auth2.get("notificationUrl")
                code = auth2.get("code")
                desc = auth2.get("desc", auth2.get("description", ""))
                if notify_url:
                    url = notify_url if notify_url[:4] == "http" else f"{ACCOUNT_BASE}{notify_url}"
                    raise XiaomiLoginError(
                        f"Login requires verification: {url}"
                    )
                raise XiaomiLoginError(
                    f"Login failed (code={code}): {desc}"
                )

            self.user_id = str(auth2.get("userId", ""))
            self.ssecurity = auth2.get("ssecurity")
            self.pass_token = auth2.get("passToken")
            location = auth2.get("location", "")

            if not location:
                raise XiaomiLoginError("Login failed: no redirect location")

        # Step 3 — follow location to collect serviceToken
        sess.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
        resp = sess.get(location)
        _LOGGER.debug("Step 3 status=%s", resp.status_code)

        service_token = resp.cookies.get("serviceToken")
        if service_token:
            self.service_token = service_token
        if not self.service_token:
            raise XiaomiLoginError(
                f"Failed to obtain service token (status={resp.status_code})"
            )
        if not self.ssecurity:
            raise XiaomiLoginError("Failed to obtain ssecurity")

        return {
            "user_id": self.user_id,
            "service_token": self.service_token,
            "ssecurity": self.ssecurity,
            "server": self.server,
        }

    def set_token(
        self,
        user_id: str,
        service_token: str,
        ssecurity: str,
        server: str = "cn",
    ):
        """Restore a previous session without re-logging in."""
        self.user_id = user_id
        self.service_token = service_token
        self.ssecurity = ssecurity
        self.server = server

    # ── API request ──────────────────────────────────────────

    def _get_api_url(self, api: str) -> str:
        if api.startswith("http"):
            return api
        api = api.lstrip("/")
        prefix = "" if self.server == "cn" else f"{self.server}."
        return f"https://{prefix}api.io.mi.com/app/{api}"

    def _api_headers(self) -> dict:
        return {
            "X-XIAOMI-PROTOCAL-FLAG-CLI": "PROTOCAL-HTTP2",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self._useragent,
        }

    def _api_cookies(self) -> dict:
        return {
            "userId": str(self.user_id or ""),
            "yetAnotherServiceToken": self.service_token or "",
            "serviceToken": self.service_token or "",
            "locale": self._locale,
            "timezone": self._timezone,
            "is_daylight": str(time.daylight),
            "dst_offset": str(time.localtime().tm_isdst * 60 * 60 * 1000),
            "channel": "MI_APP_STORE",
        }

    def _rc4_params(self, method: str, url: str, params: dict) -> dict:
        nonce = _gen_nonce()
        snonce = _signed_nonce(self.ssecurity, nonce)

        params["rc4_hash__"] = _sha1_sign(method, url, params, snonce)
        for k in list(params.keys()):
            params[k] = _encrypt_data(snonce, params[k])
        params.update(
            {
                "signature": _sha1_sign(method, url, params, snonce),
                "ssecurity": self.ssecurity,
                "_nonce": nonce,
            }
        )
        return params

    async def request_api(
        self,
        api: str,
        data: dict | None = None,
        method: str = "POST",
        timeout: int = 10,
    ) -> dict:
        if not self.service_token:
            raise XiaomiCloudError("Not logged in")

        await self._ensure_session()

        url = self._get_api_url(api)
        params: dict = {}
        if data is not None:
            params["data"] = json.dumps(data, separators=(",", ":"))

        headers = {
            **self._api_headers(),
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
            "Accept-Encoding": "identity",
        }
        rc4_params = self._rc4_params(method, url, params)
        to = aiohttp.ClientTimeout(total=timeout)
        cookies = self._api_cookies()

        if method.upper() == "GET":
            async with self.session.get(
                url,
                params=rc4_params,
                headers=headers,
                cookies=cookies,
                timeout=to,
            ) as resp:
                rsp = await resp.text()
        else:
            async with self.session.post(
                url,
                data=rc4_params,
                headers=headers,
                cookies=cookies,
                timeout=to,
            ) as resp:
                rsp = await resp.text()

        if not rsp:
            raise XiaomiCloudError(f"Empty response from {api}")

        if "message" not in rsp and "error" not in rsp:
            snonce = _signed_nonce(self.ssecurity, rc4_params["_nonce"])
            rsp = _decrypt_data(snonce, rsp)

        try:
            return json.loads(rsp)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise XiaomiCloudError(
                f"Invalid response from {api}: {str(rsp)[:200]}"
            ) from exc

    # ── Device list ──────────────────────────────────────────

    async def get_devices(self) -> list[dict]:
        homes = await self._get_home_devices()
        devices = await self._get_all_devices(homes.get("homelist", []))
        home_devices = homes.get("devices") or {}
        return [
            {**d, **(home_devices.get(d.get("did")) or {})}
            for d in devices
        ]

    async def _get_device_list(self) -> list[dict]:
        rdt = (
            await self.request_api(
                "home/device_list",
                {
                    "getVirtualModel": True,
                    "getHuamiDevices": 1,
                    "get_split_device": False,
                    "support_smart_home": True,
                },
                timeout=60,
            )
            or {}
        )
        result = rdt.get("result")
        return result.get("list", []) if result else []

    async def _get_home_devices(self) -> dict:
        rdt = (
            await self.request_api(
                "v2/homeroom/gethome_merged",
                {
                    "fg": True,
                    "fetch_share": True,
                    "fetch_share_dev": True,
                    "fetch_cariot": True,
                    "limit": 300,
                    "app_ver": 7,
                    "plat_form": 0,
                },
                timeout=60,
            )
            or {}
        )
        result = rdt.get("result") or {}
        devices = result.setdefault("devices", {})
        for h in result.get("homelist", []):
            for r in h.get("roomlist", []):
                for did in r.get("dids", []):
                    devices[did] = {
                        "home_id": h.get("id"),
                        "room_id": r.get("id"),
                        "home_name": h.get("name"),
                        "room_name": r.get("name"),
                    }
        return result

    async def _get_all_devices(self, homes: list) -> list[dict]:
        devices = {d["did"]: d for d in await self._get_device_list()}
        for home in homes:
            hid = int(home.get("id", 0))
            uid = int(home.get("uid", 0))
            start_did = ""
            has_more = True
            while has_more:
                rdt = (
                    await self.request_api(
                        "v2/home/home_device_list",
                        {
                            "home_owner": uid,
                            "home_id": hid,
                            "limit": 300,
                            "start_did": start_did,
                            "get_split_device": False,
                            "support_smart_home": True,
                            "get_cariot_device": True,
                            "get_third_device": True,
                        },
                        timeout=20,
                    )
                    or {}
                )
                result = rdt.get("result") or {}
                for d in result.get("device_info") or []:
                    did = d.get("did")
                    devices.setdefault(did, {}).update(d)
                start_did = result.get("max_did") or ""
                has_more = result.get("has_more") and start_did
        return list(devices.values())

    # ── MIoT spec operations ─────────────────────────────────

    async def get_props(self, params: list[dict]) -> list[dict]:
        return await self._miot_request("prop/get", params)

    async def set_props(self, params: list[dict]) -> list[dict]:
        return await self._miot_request("prop/set", params)

    async def do_action(self, params: dict | list[dict]) -> list[dict]:
        return await self._miot_request("action", params)

    async def _miot_request(
        self, api: str, params: dict | list[dict]
    ) -> list[dict]:
        rdt = (
            await self.request_api(
                f"miotspec/{api}",
                {"params": params if isinstance(params, list) else [params]},
            )
            or {}
        )
        result = rdt.get("result")
        if not result and rdt.get("code"):
            raise XiaomiCloudError(json.dumps(rdt, ensure_ascii=False))
        return result or []


# ── Helpers (module-level, no state) ─────────────────────────


def _sha1_sign(method: str, url: str, data: dict, nonce: str) -> str:
    path = parse.urlparse(url).path
    if path.startswith("/app/"):
        path = path[4:]
    arr = [method.upper(), path]
    for k, v in data.items():
        arr.append(f"{k}={v}")
    arr.append(nonce)
    raw = hashlib.sha1("&".join(arr).encode()).digest()
    return base64.b64encode(raw).decode()


def _encrypt_data(pwd: str, data: str) -> str:
    return base64.b64encode(
        RC4(base64.b64decode(pwd)).init1024().crypt(data)
    ).decode()


def _decrypt_data(pwd: str, data: str) -> bytes:
    return bytes(
        RC4(base64.b64decode(pwd)).init1024().crypt(base64.b64decode(data))
    )


def _update_cookies(cookies: dict, resp_cookies):
    for key, morsel in resp_cookies.items():
        cookies[key] = morsel.value