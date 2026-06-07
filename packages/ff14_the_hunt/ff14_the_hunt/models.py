from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HuntRankKind(str, Enum):
    """Bear Tracker ``lastDeathTimers`` 的 ``RankType`` 取值。"""

    A = "aRank"
    S = "sRank"
    FATE = "fate"


class TimerBarColor(str, Enum):
    """Bear Tracker 计时条 MUI 主题色键；页面上对应红/绿/蓝/橙。"""

    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"


class TimerKind(str, Enum):
    """计时条种类，与站点表头「触发时间」「条件时间」「FATE 相关计时」对应。"""

    TRIGGER = "trigger"
    CONDITION = "condition"
    FATE = "fate"


class SpawnWindowPhase(str, Enum):
    """开窗或条件阶段的内部状态；展示色见 ``TimerDisplay.bar_color``。"""

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
    pixel_x: float | None = Field(
        default=None,
        description="区域原图上的 X 像素；norm_x * 图宽",
    )
    pixel_y: float | None = Field(
        default=None,
        description="区域原图上的 Y 像素；norm_y * 图高",
    )
    active: bool | None = Field(default=None, description="querySpawnPoints 返回的存活点位状态")


class SpawnMapLayout(BaseModel):
    """Bear Tracker 刷点格点与归一化参数（与站点地图叠加一致）。"""

    model_config = ConfigDict(extra="ignore")

    grid_scale: float = Field(description="归一化分母，通常取 Dimensions[0]")
    grid_size_x: float = Field(description="格点网格宽（Dimensions[0]）")
    grid_size_y: float = Field(description="格点网格高（Dimensions[1]）")
    display_points: int = Field(description="SpawnPoint 展示点数上限")
    version: int | None = Field(default=None, description="SpawnPoint 资源版本")


class RegionMapImage(BaseModel):
    """站点 ``HuntRegions`` 区域原图（网页直链 PNG base64）。"""

    model_config = ConfigDict(extra="ignore")

    region: str = Field(description="Bear Tracker 区域名")
    source_url: str = Field(description="原图 HTTP 地址")
    mime_type: str = Field(default="image/png", description="内嵌图片 MIME")
    width: int = Field(description="原图宽度（像素）")
    height: int = Field(description="原图高度（像素）")
    data_base64: str = Field(description="原图 PNG 字节的 base64")


class TimerDisplay(BaseModel):
    """单条计时展示；``bar_color`` / ``hex_color`` 与站点计时条同色。"""

    model_config = ConfigDict(extra="ignore")

    kind: TimerKind = Field(description="触发 / 条件 / FATE")
    label: str = Field(description="与 ``kind`` 同值，保留 JSON 兼容")
    phase: SpawnWindowPhase | None = Field(default=None)
    bar_color: TimerBarColor = Field(
        description="站点 MUI 色键：error 红、success 绿、info 蓝、warning 橙",
    )
    hex_color: str = Field(description="``bar_color`` 在 Bear Tracker 主题下的主色十六进制")
    counts_up: bool = Field(description="True 为正计时，False 为倒计时")
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
    fate_timer: TimerDisplay | None = None
    spawn_points: list[MapCoordinate] = Field(
        default_factory=list,
        description="仅刚刷新记录填充；有存活点时只保留存活点",
    )
    spawn_map_layout: SpawnMapLayout | None = Field(
        default=None,
        description="仅刚刷新时填充；供外部叠加标点的格点参数",
    )
    region_map: RegionMapImage | None = Field(
        default=None,
        description="仅刚刷新且启用区域原图时填充",
    )
    recently_spawned: bool = False
    newly_spawned: bool = Field(
        default=False,
        description="本轮会话内首次检出的刚刷新；同一死亡周期不重复为 True",
    )
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
    include_untimed_marks: bool = Field(
        default=False,
        description=(
            "为 True 时保留无触发/条件/FATE 计时的占位行"
            "（如 SS 级噬灵王、维护占位）；默认 False"
        ),
    )


class HuntCrawlPacket(BaseModel):
    """单次爬取结果，供手动调用与自动轮询回调共用。"""

    model_config = ConfigDict(extra="ignore")

    crawled_at: float = Field(description="爬取完成时的 Unix 秒")
    next_fetch_at: float = Field(description="按计划下次爬取的 Unix 秒")
    marks: list[HuntMarkRecord] = Field(default_factory=list, description="解析后的狩猎记录")
    query: HuntQueryFilter = Field(description="本次爬取使用的筛选条件")

    @property
    def newly_spawned_marks(self) -> list[HuntMarkRecord]:
        return [mark for mark in self.marks if mark.newly_spawned]
