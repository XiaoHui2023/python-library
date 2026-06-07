from __future__ import annotations

from ff14_the_hunt.bear_tracker.client import BearTrackerClient
from ff14_the_hunt.bear_tracker.enrich import build_hunt_record
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.models import HuntMarkRecord, HuntQueryFilter, HuntRankKind


class FF14TheHunt:
    """FF14 狩猎追踪门面：当前对接 [Bear Tracker](https://tracker.beartoolkit.com/timer)。"""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        kwargs: dict[str, float | str] = {"timeout_seconds": timeout_seconds}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self._client = BearTrackerClient(**kwargs)
        self._resources: BearResources | None = None

    @property
    def client(self) -> BearTrackerClient:
        return self._client

    def ensure_resources(self) -> BearResources:
        if self._resources is None:
            session = self._client.sync_session()
            raw = session.get("resources", {})
            self._resources = BearResources(raw)
        return self._resources

    def list_data_centers(self, *, region: str | None = None) -> list[str]:
        """列出数据中心名；``region='CN'`` 仅中国区。"""
        resources = self.ensure_resources()
        names: list[str] = []
        for name, info in resources.data_centers.items():
            if region is not None and info.get("Region") != region:
                continue
            names.append(name)
        return sorted(names)

    def list_worlds(self, data_centers: list[str]) -> list[str]:
        resources = self.ensure_resources()
        return resources.worlds_for_data_centers(data_centers)

    def query_marks(
        self,
        query: HuntQueryFilter,
        *,
        include_spawn_states: bool = False,
        recent_grace_seconds: float = 900.0,
    ) -> list[HuntMarkRecord]:
        """按筛选条件查询并解析狩猎计时。

        Args:
            query: 数据中心、世界、Rank、资料片等筛选。
            include_spawn_states: 为 True 时对每条记录请求 ``querySpawnPoints``（较慢）。
            recent_grace_seconds: 开窗或标记后多少秒内视为「刚刷新」。
        """
        resources = self.ensure_resources()
        worlds = list(query.worlds)
        if not worlds:
            worlds = resources.worlds_for_data_centers(query.data_centers)
        if not worlds:
            return []

        rows: list[dict] = []
        for rank in query.rank_kinds:
            rows.extend(
                self._client.last_death_timers(
                    world_names=worlds,
                    rank_type=rank.value,
                )
            )

        records: list[HuntMarkRecord] = []
        for row in rows:
            spawn_states = None
            if include_spawn_states:
                spawn_states = self._load_spawn_states(row, resources)
            record = build_hunt_record(
                timer_row=row,
                resources=resources,
                spawn_states=spawn_states,
                query=query,
                recent_grace_seconds=recent_grace_seconds,
            )
            if record is not None:
                records.append(record)
        return records

    def recently_spawned(
        self,
        query: HuntQueryFilter,
        *,
        recent_grace_seconds: float = 900.0,
    ) -> list[HuntMarkRecord]:
        marks = self.query_marks(
            query,
            recent_grace_seconds=recent_grace_seconds,
        )
        return [mark for mark in marks if mark.recently_spawned]

    def _load_spawn_states(
        self,
        row: dict,
        resources: BearResources,
    ) -> dict | None:
        hunt_key = str(row.get("huntKey") or "")
        world_name = str(row.get("worldName") or "")
        if not hunt_key or not world_name:
            return None
        meta = resources.hunt_meta(hunt_key)
        last_death = row.get("lastMarkTime") or row.get("lastDeathTime")
        try:
            states = self._client.query_spawn_points(
                hunt_name=hunt_key,
                world_name=world_name,
                last_death=float(last_death) if last_death else None,
            )
        except RuntimeError:
            return None
        return states if isinstance(states, dict) else None
