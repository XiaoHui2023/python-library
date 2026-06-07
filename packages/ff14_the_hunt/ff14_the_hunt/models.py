from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HuntRankKind(str, Enum):
    """Bear Tracker ``lastDeathTimers`` 的 ``RankType`` 取值。"""

    A = "aRank"
    S = "sRank"
    FATE = "fate"


class SpawnWindowPhase(str, Enum):
    """与站点主计时条颜色/文案一致的开窗阶段。"""

    CLOSED = "closed"
    ALMOST_OPEN = "almost_open"
    OPEN = "open"
    CAPPED = "capped"


class MapCoordinate(BaseModel):
    """地图格点坐标（与站点触发的地图一致，非游戏内绝对坐标）。"""

    model_config = ConfigDict(extra="ignore")

    point_key: str = Field(description="SpawnPoint 键名，例如 SpawnPoint01")
    x: float = Field(description="地图 X，已按站点公式归一化")
    y: float = Field(description="地图 Y，已按站点公式归一化")
    grid_x: float | None = Field(default=None, description="原始格点 X")
    grid_y: float | None = Field(default=None, description="原始格点 Y")
    active: bool | None = Field(default=None, description="querySpawnPoints 返回的存活点位状态")


class TimerDisplay(BaseModel):
    """单条计时展示（触发窗或条件窗）。"""

    model_config = ConfigDict(extra="ignore")

    label: str = Field(description="例如 trigger / condition / fate")
    phase: SpawnWindowPhase | None = Field(default=None)
    elapsed_seconds: float | None = Field(default=None)
    remaining_seconds: float | None = Field(default=None)
    progress_percent: float | None = Field(default=None)
    summary: str = Field(default="", description="人类可读简述")


class HuntMarkRecord(BaseModel):
    """单条狩猎计时记录（合并 API 与资源库后的视图）。"""

    model_config = ConfigDict(extra="ignore")

    hunt_key: str
    hunt_name: str
    world_name: str
    region: str | list[str] = ""
    patch: str = ""
    rank: int | None = None
    last_death_time: float | None = None
    last_mark_time: float | None = None
    missing_counter: float = 0.0
    is_maintenance: bool = False
    fate_last_seen: float | None = None
    fate_last_death: float | None = None
    trigger_timer: TimerDisplay | None = None
    condition_timer: TimerDisplay | None = None
    spawn_points: list[MapCoordinate] = Field(default_factory=list)
    recently_spawned: bool = False
    raw_timer: dict[str, Any] = Field(default_factory=dict)


class HuntQueryFilter(BaseModel):
    """查询 Bear Tracker 时的筛选条件。"""

    model_config = ConfigDict(extra="forbid")

    data_centers: list[str] = Field(
        default_factory=list,
        description="中国区为猫小胖、莫古力等数据中心名；国际区为 Aether 等",
    )
    worlds: list[str] = Field(
        default_factory=list,
        description="世界名；为空时由 data_centers 展开全部世界",
    )
    rank_kinds: list[HuntRankKind] = Field(
        default_factory=lambda: [HuntRankKind.S],
        description="A / S / FATE，可多选",
    )
    patches: list[str] = Field(
        default_factory=list,
        description="资料片缩写：ARR、HW、ShB、EW、DT 等；空表示不过滤",
    )
    hunt_keys: list[str] = Field(
        default_factory=list,
        description="限定 huntKey；空表示不过滤",
    )
    regions: list[str] = Field(
        default_factory=list,
        description="地图区域名；空表示不过滤",
    )
