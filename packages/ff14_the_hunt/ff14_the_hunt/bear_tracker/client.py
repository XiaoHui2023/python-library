from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from ff14_the_hunt.common.urlopen_retry import (
    retry_after_seconds_from_headers,
    urlopen_read,
)
from ff14_the_hunt.common.http_request import DEFAULT_USER_AGENT

DEFAULT_BASE_URL = "https://tracker.beartoolkit.com/api"
_BLOCKED_HTTP_CODES = frozenset({403, 429})


class BearTrackerRequestError(RuntimeError):
    """Bear Tracker API request failed after HTTP retry handling."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class BearTrackerBlockedError(BearTrackerRequestError):
    """Bear Tracker returned a block or rate-limit status."""


class BearTrackerClient:
    """Bear Tracker 站点同源 API 客户端（``/api/*``）。"""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 120.0,
        min_request_interval_seconds: float = 1.0,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._min_request_interval_seconds = min_request_interval_seconds
        self._user_agent = user_agent
        self._last_request_at = 0.0
        self._request_lock = threading.Lock()

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds

    @property
    def min_request_interval_seconds(self) -> float:
        return self._min_request_interval_seconds

    @property
    def user_agent(self) -> str:
        return self._user_agent

    def sync_session(self) -> dict[str, Any]:
        """拉取会话与 ``resources``（含 DatabaseHunt、SpawnPoint、DataCenters）。"""
        return self._post("/syncSession", {})

    def last_death_timers(
        self,
        *,
        world_names: list[str],
        rank_type: str,
    ) -> list[dict[str, Any]]:
        """按世界列表查询死亡/计时记录。

        Args:
            world_names: 世界名列表（由数据中心展开或直接指定）。
            rank_type: ``aRank``、``sRank`` 或 ``fate``。
        """
        payload = {
            "QueryDeathTimers": world_names,
            "RankType": rank_type,
        }
        data = self._post("/lastDeathTimers", payload)
        timers = data.get("timers", [])
        if isinstance(timers, dict):
            return list(timers.values())
        if isinstance(timers, list):
            return timers
        return []

    def hunt_info(self, *, hunt_name: str, world_name: str) -> dict[str, Any]:
        return self._post(
            "/huntInfo",
            {"HuntName": hunt_name, "WorldName": world_name},
        )

    def query_spawn_points(
        self,
        *,
        hunt_name: str,
        world_name: str,
        last_death: float | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "WorldName": world_name,
            "HuntName": hunt_name,
            "QuerySpawnPoint": "Query",
        }
        if last_death is not None:
            body["LastDeath"] = last_death
        result = self._post("/querySpawnPoints", body)
        if isinstance(result, dict):
            return result.get("data", result)
        return {}

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        encoded = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded,
            headers=self._headers(),
            method="POST",
        )
        try:
            self._pace_request()
            raw = urlopen_read(request, timeout=self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retry_after = retry_after_seconds_from_headers(exc.headers)
            message = f"Bear Tracker API {path} failed: HTTP {exc.code}: {detail}"
            error_type = (
                BearTrackerBlockedError
                if exc.code in _BLOCKED_HTTP_CODES
                else BearTrackerRequestError
            )
            raise error_type(
                message,
                status_code=exc.code,
                retry_after_seconds=retry_after,
            ) from exc
        except urllib.error.URLError as exc:
            raise BearTrackerRequestError(f"Bear Tracker API {path} failed: {exc}") from exc
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise RuntimeError(f"unexpected response type from {path}")
        return parsed

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self._user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://tracker.beartoolkit.com",
            "Referer": "https://tracker.beartoolkit.com/timer",
        }

    def _pace_request(self) -> None:
        if self._min_request_interval_seconds <= 0:
            return
        with self._request_lock:
            now = time.monotonic()
            wait_seconds = self._min_request_interval_seconds - (
                now - self._last_request_at
            )
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            self._last_request_at = time.monotonic()
