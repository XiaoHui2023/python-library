from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "https://tracker.beartoolkit.com/api"


class BearTrackerClient:
    """Bear Tracker 站点同源 API 客户端（``/api/*``）。"""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

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
            headers={
                "User-Agent": "python-library-ff14-the-hunt",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://tracker.beartoolkit.com",
                "Referer": "https://tracker.beartoolkit.com/timer",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Bear Tracker API {path} failed: HTTP {exc.code}: {detail}"
            ) from exc
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise RuntimeError(f"unexpected response type from {path}")
        return parsed
