from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.models import FetchPolicy, SourceConfigBase


class TopicCategory(StrEnum):
    """热点话题粗分类。"""

    ENTERTAINMENT = "entertainment"
    SOCIETY = "society"
    GAME = "game"
    TECH = "tech"
    SPORTS = "sports"
    FILM = "film"
    OTHER = "other"


class CnPlatform(StrEnum):
    """中国内容平台标识。"""

    WEIBO = "weibo"
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    XIAOHONGSHU = "xiaohongshu"
    KUAISHOU = "kuaishou"
    ZHIHU = "zhihu"
    TIEBA = "tieba"
    HUPU = "hupu"
    NGA = "nga"
    DOUBAN = "douban"
    BAIDU = "baidu"
    TOUTIAO = "toutiao"
    JUEJIN = "juejin"
    V2EX = "v2ex"


class TopicItem(BaseModel):
    """热点发现项：来自热榜、热搜、话题榜。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="库内唯一 ID")
    provider: str = Field(description="发现源名称，如 hotpush")
    platform: str = Field(description="平台标识，如 weibo、douyin")
    title: str = Field(description="热点标题")
    source_url: str = Field(description="原始话题或榜单链接")
    hot_score: float | None = Field(default=None, description="热度分数")
    rank: int | None = Field(default=None, description="榜单名次")
    category: TopicCategory | None = Field(default=None, description="粗分类")
    cover_url: str | None = Field(default=None, description="榜单项自带封面")
    timestamp: datetime | None = Field(default=None, description="上榜或更新时间")


class TopicFeed(BaseModel):
    """一次热点发现结果。"""

    model_config = ConfigDict(extra="forbid")

    topics: list[TopicItem] = Field(default_factory=list, description="热点列表")
    fetched_at: datetime = Field(description="拉取完成时间")
    providers_ok: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)


class HotpushConfig(SourceConfigBase):
    """hotpush 热点推送服务配置。"""

    base_url: str = Field(default="", description="hotpush 服务地址")


class TikHubConfig(SourceConfigBase):
    """TikHub 第三方社交平台数据配置。"""

    base_url: str = Field(
        default="https://api.tikhub.io",
        description="TikHub API 根地址",
    )


class CnSourcesConfig(BaseModel):
    """热点发现 + 内容搜图配置。"""

    model_config = ConfigDict(extra="forbid")

    hotpush: HotpushConfig | None = Field(
        default=None,
        description="hotpush 热点发现",
    )
    tikhub: TikHubConfig | None = Field(
        default=None,
        description="TikHub 按热词搜图",
    )


class CnPipelinePolicy(BaseModel):
    """「发现 → 搜图」管线策略。"""

    model_config = ConfigDict(extra="forbid")

    topic_limit: int = Field(default=10, description="参与搜图的热点条数上限")
    images_per_topic: int = Field(default=3, description="每个热点最多取图数")
    classify_topics: bool = Field(default=True, description="是否对热点做粗分类")
    content_platforms: list[str] = Field(
        default_factory=lambda: [
            CnPlatform.XIAOHONGSHU.value,
            CnPlatform.WEIBO.value,
        ],
        description="内容搜索目标平台",
    )


class DiscoverTopicsQuery(BaseModel):
    """热点发现查询参数。"""

    model_config = ConfigDict(extra="forbid")

    platforms: list[str] | None = Field(default=None, description="限定平台路由")
    limit: int | None = Field(default=None, description="每平台返回条数")
    sources: list[str] | None = Field(
        default=None,
        description="限定发现源，如 hotpush",
    )


def default_cn_sources() -> CnSourcesConfig:
    """默认不启用任何源；须在配置中显式开启。"""
    return CnSourcesConfig()


def default_cn_pipeline() -> CnPipelinePolicy:
    return CnPipelinePolicy()


class CnHotQuery(BaseModel):
    """热点图片聚合查询。"""

    model_config = ConfigDict(extra="forbid")

    limit: int | None = Field(default=None, description="最终图片条数上限")
    platforms: list[str] | None = Field(default=None, description="热点发现平台")
    topic_limit: int | None = Field(default=None, description="参与管线的话题数")
    allow_nsfw: bool | None = Field(default=None, description="是否允许 NSFW")
    discovery_sources: list[str] | None = Field(
        default=None,
        description="热点发现源列表",
    )
    content_sources: list[str] | None = Field(
        default=None,
        description="内容搜图源列表",
    )


from hotmeme.models import HotMemeModels  # noqa: E402

HotMemeModels.model_rebuild()
