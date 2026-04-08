from typing import Any

import aiohttp

from .cloud import MiotCloud, XiaomiCloudError, XiaomiLoginError
from .miio import AsyncMiIO
from .miot_spec import MiotSpec


class XiaomiMiotClient:
    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._external_session = session is not None
        self._session = session
        self.cloud = MiotCloud(session)

    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self.cloud.session = self._session
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        await self.cloud.close()
        if self._session and not self._external_session:
            await self._session.close()
            self._session = None

    # ── Auth ─────────────────────────────────────────────────

    async def login(
        self, username: str, password: str, server: str = "cn"
    ) -> dict:
        return await self.cloud.login(username, password, server)

    def set_token(
        self,
        user_id: str,
        service_token: str,
        ssecurity: str,
        server: str = "cn",
    ):
        """Restore a previous session without re-logging in."""
        self.cloud.set_token(user_id, service_token, ssecurity, server)

    # ── Device info ──────────────────────────────────────────

    async def get_devices(self) -> list[dict]:
        return await self.cloud.get_devices()

    async def get_device_spec(self, model: str) -> MiotSpec | None:
        session = self._session or self.cloud.session
        if session is None:
            raise RuntimeError(
                "Use 'async with XiaomiMiotClient()' or provide a session"
            )
        return await MiotSpec.from_model(session, model)

    # ── Cloud control ────────────────────────────────────────

    async def cloud_get_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        """Read properties via cloud.
        props: [{"siid": 2, "piid": 1}, ...]
        """
        params = [{"did": str(did), **p} for p in props]
        return await self.cloud.get_props(params)

    async def cloud_set_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        """Write properties via cloud.
        props: [{"siid": 2, "piid": 1, "value": True}, ...]
        """
        params = [{"did": str(did), **p} for p in props]
        return await self.cloud.set_props(params)

    async def cloud_action(
        self,
        did: str,
        siid: int,
        aiid: int,
        params: list | None = None,
    ) -> list[dict]:
        """Execute an action via cloud."""
        return await self.cloud.do_action(
            {
                "did": str(did),
                "siid": siid,
                "aiid": aiid,
                "in": params or [],
            }
        )

    # ── LAN control ──────────────────────────────────────────

    def local_device(self, host: str, token: str) -> "LocalDevice":
        return LocalDevice(host, token)


class LocalDevice:
    """Control a Xiaomi device over LAN via miIO protocol."""

    def __init__(self, host: str, token: str):
        self._miio = AsyncMiIO(host, token)

    async def info(self) -> dict | None:
        """Get device info (model, firmware, mac, etc.)."""
        return await self._miio.info()

    async def get_props(self, props: list[dict]) -> list[dict]:
        """Read MIoT properties.
        props: [{"did": "x", "siid": 2, "piid": 1}, ...]
        """
        return await self._miio.send_bulk("get_properties", props) or []

    async def set_props(self, props: list[dict]) -> list[dict]:
        """Write MIoT properties.
        props: [{"did": "x", "siid": 2, "piid": 1, "value": True}, ...]
        """
        resp = await self._miio.send("set_properties", props)
        return resp.get("result", []) if resp else []

    async def action(
        self,
        siid: int,
        aiid: int,
        did: str = "0",
        params: list | None = None,
    ) -> dict:
        """Execute a MIoT action."""
        pms = {
            "did": did,
            "siid": siid,
            "aiid": aiid,
            "in": params or [],
        }
        resp = await self._miio.send("action", pms)
        return resp.get("result", {}) if resp else {}

    async def send(self, method: str, params: Any = None):
        """Send an arbitrary miIO command."""
        resp = await self._miio.send(method, params)
        if resp and "result" in resp:
            return resp["result"]
        return resp