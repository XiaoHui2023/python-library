import asyncio
from typing import Any

from .client import EWeLinkClient
from .types import SwitchItem, SwitchState


class SyncEWeLinkClient:
    """Convenience wrapper that reuses a single session and login."""

    def __init__(
        self,
        username: str,
        password: str,
        country_code: str | None = None,
        region: str | None = None,
    ):
        self._username = username
        self._password = password
        self._country_code = country_code
        self._region = region
        self._loop = asyncio.new_event_loop()
        self._client = EWeLinkClient()
        self._loop.run_until_complete(self._client.__aenter__())
        self._logged_in = False

    def _ensure_login(self) -> None:
        if not self._logged_in:
            self._loop.run_until_complete(
                self._client.login(
                    self._username,
                    self._password,
                    self._country_code,
                    self._region,
                )
            )
            self._logged_in = True

    # ── devices: query ──

    def get_devices(self, family_id: str | None = None) -> list[dict[str, Any]]:
        self._ensure_login()
        return self._loop.run_until_complete(self._client.get_devices(family_id))

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        self._ensure_login()
        return self._loop.run_until_complete(self._client.get_device(device_id))

    # ── devices: control ──

    def set_switch(self, device_id: str, state: SwitchState) -> dict[str, Any]:
        self._ensure_login()
        return self._loop.run_until_complete(self._client.set_switch(device_id, state))

    def set_outlet(self, device_id: str, outlet: int, state: SwitchState) -> dict[str, Any]:
        self._ensure_login()
        return self._loop.run_until_complete(self._client.set_outlet(device_id, outlet, state))

    def set_outlets(self, device_id: str, switches: list[SwitchItem]) -> dict[str, Any]:
        self._ensure_login()
        return self._loop.run_until_complete(self._client.set_outlets(device_id, switches))

    def pulse_outlet(self, device_id: str, outlet: int, hold_seconds: float = 0.5) -> None:
        self._ensure_login()
        self._loop.run_until_complete(
            self._client.pulse_outlet(device_id, outlet, hold_seconds)
        )

    # ── lifecycle ──

    def close(self) -> None:
        self._loop.run_until_complete(self._client.__aexit__(None, None, None))
        self._loop.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()