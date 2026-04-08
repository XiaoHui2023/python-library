import asyncio
from typing import Any

from .client import XiaomiMiotClient
from .miot_spec import MiotSpec


class SyncXiaomiMiotClient:
    """Synchronous wrapper — each call opens a fresh session."""

    def __init__(
        self, username: str, password: str, server: str = "cn"
    ):
        self.username = username
        self.password = password
        self.server = server

    def get_devices(self) -> list[dict]:
        return asyncio.run(self._get_devices())

    def get_device_spec(self, model: str) -> MiotSpec | None:
        return asyncio.run(self._get_device_spec(model))

    def cloud_get_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        return asyncio.run(self._cloud_get_props(did, props))

    def cloud_set_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        return asyncio.run(self._cloud_set_props(did, props))

    def cloud_action(
        self, did: str, siid: int, aiid: int, params: list | None = None
    ) -> list[dict]:
        return asyncio.run(self._cloud_action(did, siid, aiid, params))

    # ── internal async implementations ───────────────────────

    async def _login(self, client: XiaomiMiotClient):
        await client.login(self.username, self.password, self.server)

    async def _get_devices(self) -> list[dict]:
        async with XiaomiMiotClient() as c:
            await self._login(c)
            return await c.get_devices()

    async def _get_device_spec(self, model: str) -> MiotSpec | None:
        async with XiaomiMiotClient() as c:
            return await c.get_device_spec(model)

    async def _cloud_get_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        async with XiaomiMiotClient() as c:
            await self._login(c)
            return await c.cloud_get_props(did, props)

    async def _cloud_set_props(
        self, did: str, props: list[dict]
    ) -> list[dict]:
        async with XiaomiMiotClient() as c:
            await self._login(c)
            return await c.cloud_set_props(did, props)

    async def _cloud_action(
        self, did: str, siid: int, aiid: int, params: list | None = None
    ) -> list[dict]:
        async with XiaomiMiotClient() as c:
            await self._login(c)
            return await c.cloud_action(did, siid, aiid, params)