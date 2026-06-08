from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MediaType(StrEnum):
    """可展示的媒体种类。"""

    IMAGE = "image"
    GIF = "gif"
    VIDEO = "video"
    VIDEO_COVER = "video_cover"
    TEMPLATE = "template"


class ReviewStatus(StrEnum):
    """人工审核状态。"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProviderId(StrEnum):
    """内容源标识。"""

    TIKHUB = "tikhub"


class Platform(StrEnum):
    """社交平台标识。"""

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


DEFAULT_PLATFORMS = [
    Platform.XIAOHONGSHU,
    Platform.DOUYIN,
]

DEFAULT_XHS_SEARCH_TAGS: tuple[str, ...] = (
    "搞笑",
)


class TikHubApiCall(BaseModel):
    """单次 TikHub HTTP 请求记录。"""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(description="HTTP 方法")
    path: str = Field(description="API 路径")
    params: dict[str, Any] | None = Field(default=None, description="查询或 JSON 体参数摘要")


class ImageItem(BaseModel):
    """统一热帖项：图文或短视频帖。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="库内唯一 ID")
    provider: str = Field(description="来源名称，如 tikhub")
    source_id: str = Field(description="来源侧原始 ID")
    title: str = Field(description="标题或描述")
    image_url: str = Field(
        default="",
        description="主图或视频封面；纯视频帖可为空字符串，但须有 video_url",
    )
    video_url: str | None = Field(default=None, description="可播放视频地址")
    preview_url: str | None = Field(default=None, description="预览小图地址")
    source_url: str = Field(description="原始页面或帖子链接")
    author: str | None = Field(default=None, description="作者名")
    community: str | None = Field(default=None, description="平台或频道标识")
    search_tag: str | None = Field(
        default=None,
        description="拉取时使用的搜索话题 tag（如小红书 #搞笑# 的「搞笑」）",
    )
    score: float | None = Field(default=None, description="互动热度分数")
    created_at: datetime | None = Field(default=None, description="发布时间")
    media_type: MediaType = Field(description="媒体类型")
    nsfw: bool = Field(default=False, description="是否含成人内容")
    width: int | None = Field(default=None, description="图片宽度像素")
    height: int | None = Field(default=None, description="图片高度像素")
    risk_flags: list[str] = Field(
        default_factory=list,
        description="风险标签，如 political、ad",
    )
    review_status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="人工审核状态",
    )


class ImageFeed(BaseModel):
    """一次拉取结果。"""

    model_config = ConfigDict(extra="forbid")

    items: list[ImageItem] = Field(default_factory=list, description="去重排序后的热帖项")
    fetched_at: datetime = Field(description="拉取完成时间")
    providers_ok: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)
    fetch_errors: list[str] = Field(
        default_factory=list,
        description="拉取过程中的错误说明，如单平台失败原因",
    )
    api_calls: list[TikHubApiCall] = Field(
        default_factory=list,
        description="本轮 TikHub HTTP 请求记录（按次计费）",
    )
    diagnostics: FetchDiagnostics | None = Field(
        default=None,
        description="解析与过滤阶段统计（调试）",
    )


class SourceConfigBase(BaseModel):
    """来源公共配置。"""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="是否启用")
    timeout: float = Field(default=5.0, description="请求超时秒数")
    allow_nsfw: bool = Field(default=False, description="是否允许 NSFW 内容")
    media_types: list[MediaType] = Field(
        default_factory=lambda: [
            MediaType.IMAGE,
            MediaType.GIF,
            MediaType.VIDEO,
            MediaType.VIDEO_COVER,
        ],
        description="允许的媒体类型",
    )
    min_score: float | None = Field(default=None, description="最低互动分数")
    api_key: str | None = Field(default=None, description="API key")


class TikHubConfig(SourceConfigBase):
    """TikHub 热帖拉取配置。"""

    base_url: str = Field(
        default="https://api.tikhub.io",
        description="TikHub API 根地址",
    )


class XiaohongshuPolicy(BaseModel):
    """小红书按话题 tag 搜索策略。"""

    model_config = ConfigDict(extra="forbid")

    tags_enabled: bool = Field(
        default=False,
        description="为 true 时对 search_tags 中每个 tag 各搜一次；为 false 时仅搜列表第一项",
    )
    search_tags: list[str] = Field(
        default_factory=lambda: list(DEFAULT_XHS_SEARCH_TAGS),
        description="话题 tag 列表，按命中率从高到低排列",
    )
    page: int = Field(default=1, ge=1, description="搜索页码，从 1 开始")
    sort_type: str = Field(
        default="popularity_descending",
        description="排序：popularity_descending（最多点赞）、general（综合）、time_descending 等",
    )
    time_filter: str = Field(
        default="一天内",
        description="发布时间：不限、一天内、一周内、半年内",
    )
    note_type: str = Field(
        default="不限",
        description="笔记类型：不限、视频笔记、普通笔记",
    )

    def search_keywords(self) -> list[str]:
        """本轮实际用于搜索的 ``#话题#`` 关键词列表。"""
        from hotmeme.sources.parsers.xiaohongshu import format_xhs_tag_query

        selected = self.search_tags if self.tags_enabled else self.search_tags[:1]
        keywords: list[str] = []
        for tag in selected:
            query = format_xhs_tag_query(tag)
            if query:
                keywords.append(query)
        return keywords

    def tikhub_call_count(self) -> int:
        """本轮小红书 TikHub 搜索请求次数（每个关键词 1 次）。"""
        return len(self.search_keywords())


class PipelinePolicy(BaseModel):
    """热帖拉取管线策略。"""

    model_config = ConfigDict(extra="forbid")

    platforms: list[str] = Field(
        default_factory=lambda: [p.value for p in DEFAULT_PLATFORMS],
        description="拉取热帖的目标平台",
    )


class FetchPolicy(BaseModel):
    """聚合默认策略。"""

    model_config = ConfigDict(extra="forbid")

    per_source_timeout: float = Field(default=5.0, description="单平台超时秒数")
    retries: int = Field(default=1, description="失败重试次数")
    skip_failed_providers: bool = Field(
        default=True,
        description="单平台失败时是否跳过并继续",
    )


class HotPostsQuery(BaseModel):
    """热帖拉取查询参数。"""

    model_config = ConfigDict(extra="forbid")

    platforms: list[str] | None = Field(default=None, description="限定平台列表")
    allow_nsfw: bool | None = Field(default=None, description="是否允许 NSFW")


class HotMemeModels(BaseModel):
    """HotMeme 根配置（可由 YAML/JSON 载入）。"""

    model_config = ConfigDict(extra="ignore")

    tikhub: TikHubConfig | None = Field(default=None, description="TikHub 热帖源")
    pipeline: PipelinePolicy | None = Field(default=None, description="热帖管线策略")
    xiaohongshu: XiaohongshuPolicy | None = Field(
        default=None,
        description="小红书话题 tag 搜索；缺省用默认 tag 列表",
    )
    fetch: FetchPolicy = Field(default_factory=FetchPolicy)


def default_pipeline() -> PipelinePolicy:
    return PipelinePolicy()
