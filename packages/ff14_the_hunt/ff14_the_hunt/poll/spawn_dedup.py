from __future__ import annotations

from ff14_the_hunt.models import HuntMarkRecord

SpawnCycleKey = tuple[str, str, float | None]


def spawn_cycle_key(mark: HuntMarkRecord) -> SpawnCycleKey:
    """同一死亡周期内只应上报一次「新检出」。"""
    return (mark.hunt_key, mark.world_name, mark.last_death_time)


class SpawnReportTracker:
    """跨轮询记住已上报的刷新周期，避免宽限期内重复当作新刷新。"""

    def __init__(self) -> None:
        self._reported_cycles: set[SpawnCycleKey] = set()

    def apply(self, marks: list[HuntMarkRecord]) -> None:
        for mark in marks:
            if not mark.recently_spawned:
                mark.newly_spawned = False
                continue
            cycle = spawn_cycle_key(mark)
            if cycle in self._reported_cycles:
                mark.newly_spawned = False
                continue
            mark.newly_spawned = True
            self._reported_cycles.add(cycle)
