import asyncio
import base64
import json
from typing import Any

import aiohttp

from .auth import APP_ID, build_phone_number, sign_payload
from .exceptions import EWeLinkAPIError, EWeLinkAuthError
from .regions import API, REGIONS, infer_country_code
from .types import SwitchItem, SwitchState

_TIMEOUT = aiohttp.ClientTimeout(total=15)
_MAX_RETRIES = 3


class EWeLinkClient:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._external_session = session is not None
        self.session = session
        self.region: str | None = None
        self.auth: dict[str, Any] | None = None

    # ── lifecycle ──

    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session and not self._external_session:
            await self.session.close()

    # ── auth ──

    async def login(
        self,
        username: str,
        password: str,
        country_code: str | None = None,
        region: str | None = None,
    ) -> dict[str, Any]:
        if not self.session:
            raise RuntimeError("Use 'async with EWeLinkClient()' or provide a session")

        country_code = country_code or infer_country_code(username)
        self.region = region or REGIONS.get(country_code, ("Unknown", "cn"))[1]

        payload: dict[str, Any] = {"password": password, "countryCode": country_code}
        if "@" in username:
            payload["email"] = username
        else:
            payload["phoneNumber"] = build_phone_number(username, country_code)

        data = json.dumps(payload, separators=(",", ":")).encode()
        headers = {
            "Authorization": "Sign " + base64.b64encode(sign_payload(data)).decode(),
            "Content-Type": "application/json",
            "X-CK-Appid": APP_ID,
        }

        resp = await self._request("POST", "/v2/user/login", data=data, headers=headers)

        if resp.get("error") == 10004 and resp.get("data", {}).get("region"):
            self.region = resp["data"]["region"]
            resp = await self._request("POST", "/v2/user/login", data=data, headers=headers)

        if resp.get("error") != 0:
            raise EWeLinkAuthError(
                f"Login failed: error={resp.get('error')} msg={resp.get('msg')}"
            )

        self.auth = resp["data"]
        self.auth["appid"] = APP_ID
        return self.auth

    # ── devices: query ──

    async def get_devices(self, family_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"num": 0}
        if family_id:
            params["familyid"] = family_id

        resp = await self._api_get("/v2/device/thing", params=params)
        return [
            item["itemData"]
            for item in resp["data"]["thingList"]
            if "deviceid" in item.get("itemData", {})
        ]

    async def get_device(self, device_id: str) -> dict[str, Any] | None:
        resp = await self._api_post(
            "/v2/device/thing",
            json={"thingList": [{"itemType": 1, "id": device_id}]},
        )
        for item in resp["data"].get("thingList", []):
            data = item.get("itemData", {})
            if data.get("deviceid") == device_id:
                return data
        return None

    # ── devices: control ──

    async def set_device_params(self, device_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._api_post(
            "/v2/device/thing/status",
            json={"type": 1, "id": device_id, "params": params},
        )

    async def set_switch(self, device_id: str, state: SwitchState) -> dict[str, Any]:
        return await self.set_device_params(device_id, {"switch": state})

    async def set_outlet(
        self, device_id: str, outlet: int, state: SwitchState,
    ) -> dict[str, Any]:
        return await self.set_device_params(
            device_id, {"switches": [{"outlet": outlet, "switch": state}]},
        )

    async def set_outlets(
        self, device_id: str, switches: list[SwitchItem],
    ) -> dict[str, Any]:
        return await self.set_device_params(device_id, {"switches": switches})

    async def pulse_outlet(
        self, device_id: str, outlet: int, hold_seconds: float = 0.5,
    ) -> None:
        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be > 0")
        await self.set_outlet(device_id, outlet, "on")
        try:
            await asyncio.sleep(hold_seconds)
        finally:
            await self.set_outlet(device_id, outlet, "off")

    # ── internal: HTTP ──

    def _ensure_ready(self) -> None:
        if not self.session:
            raise RuntimeError("Use 'async with EWeLinkClient()' or provide a session")
        if not self.auth or not self.region:
            raise EWeLinkAuthError("Not logged in")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.auth["at"],
            "X-CK-Appid": APP_ID,
        }

    async def _api_get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        self._ensure_ready()
        resp = await self._request("GET", path, headers=self._headers, **kwargs)
        _check_response(resp)
        return resp

    async def _api_post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        self._ensure_ready()
        resp = await self._request("POST", path, headers=self._headers, **kwargs)
        _check_response(resp)
        return resp

    async def _request(
        self, method: str, path: str, *, retries: int = _MAX_RETRIES, **kwargs: Any,
    ) -> dict[str, Any]:
        if not self.session or not self.region:
            raise EWeLinkAuthError("Client not initialized")

        url = API[self.region] + path
        last_exc: Exception | None = None

        for attempt in range(retries):
            try:
                async with self.session.request(
                    method, url, timeout=_TIMEOUT, **kwargs,
                ) as response:
                    text = await response.text()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError as exc:
                        raise EWeLinkAPIError(
                            -1, f"Non-JSON response (HTTP {response.status})",
                        ) from exc
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                if attempt < retries - 1:
                    await asyncio.sleep(0.5 * 2**attempt)

        raise EWeLinkAPIError(-1, f"Request failed after {retries} retries") from last_exc


def _check_response(resp: dict[str, Any]) -> None:
    error = resp.get("error", 0)
    if error != 0:
        raise EWeLinkAPIError(error, resp.get("msg"), resp.get("data"))