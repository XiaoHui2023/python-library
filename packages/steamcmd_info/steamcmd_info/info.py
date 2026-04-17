from __future__ import annotations

from typing import Any, Optional

import requests

from .constants import DEFAULT_INFO_URL_TEMPLATE
from .errors import SteamCmdInfoError
from .fetch import fetch_json_with_proxy_fallback


class SteamCmdInfo:
    """
    Load SteamCMD HTTP API info for one ``appid`` (fetches on construction).

    The remote "version" used for update checks is the ``public`` branch
    ``timeupdated`` Unix timestamp from the API (exposed as :attr:`version`).
    """

    def __init__(
        self,
        appid: int,
        *,
        url_template: str = DEFAULT_INFO_URL_TEMPLATE,
        proxy: Optional[str] = None,
        branch: str = "public",
        timeout: float = 60,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._appid = appid
        self._branch = branch
        self._timeout = timeout
        self._session = session or requests.Session()
        self._url = url_template.format(appid=appid)
        self._raw: dict[str, Any] = fetch_json_with_proxy_fallback(
            self._url,
            proxy=proxy,
            timeout=timeout,
            session=self._session,
        )
        self._app_block: Optional[dict[str, Any]] = self._raw.get("data", {}).get(
            str(appid)
        )

    @property
    def appid(self) -> int:
        return self._appid

    @property
    def request_url(self) -> str:
        return self._url

    @property
    def raw(self) -> dict[str, Any]:
        """Full JSON response from the info endpoint."""
        return self._raw

    @property
    def app_data(self) -> dict[str, Any]:
        """The ``data[<appid>]`` object from the API, or empty dict if missing."""
        if self._app_block is None:
            return {}
        return self._app_block

    @property
    def version(self) -> int:
        """
        Remote version for update decisions: ``timeupdated`` on ``branch``
        (default ``public``), as int Unix seconds.
        """
        try:
            time_str = (
                self._app_block["depots"]["branches"][self._branch]["timeupdated"]
            )
            return int(time_str)
        except (KeyError, TypeError, ValueError) as exc:
            raise SteamCmdInfoError(
                f"Cannot read timeupdated for appid={self._appid}, branch={self._branch!r}"
            ) from exc

    def needs_update(self, local_version: int) -> bool:
        """Return True if the remote :attr:`version` is greater than ``local_version``."""
        return self.version > local_version
