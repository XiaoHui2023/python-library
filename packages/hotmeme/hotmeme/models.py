from __future__ import annotations

from datetime import datetime
from enum import StrEnum

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
    """热点与内容源标识。"""

    HOTPUSH = "hotpush"
    TIKHUB = "tikhub"


class ImageItem(BaseModel):
    """统一图片项：各来源抓取结果均转换为此结构。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="库内唯一 ID")
    provider: str = Field(description="来源名称，如 hotpush、tikhub")
    source_id: str = Field(description="来源侧原始 ID")
    title: str = Field(description="标题或描述")
    image_url: str = Field(description="可展示的图片地址")
    preview_url: str | None = Field(default=None, description="预览小图地址")
    source_url: str = Field(description="原始页面或帖子链接")
    author: str | None = Field(default=None, description="作者名")
    community: str | None = Field(default=None, description="社区、频道或标签")
    score: float | None = Field(default=None, description="来源热度分数")
    created_at: datetime | None = Field(default=None, description="发布时间")
    media_type: MediaType = Field(description="媒体类型")
    nsfw: bool = Field(default=False, description="是否含成人内容")
    width: int | None = Field(default=None, description="图片宽度像素")
    height: int | None = Field(default=None, description="图片高度像素")
    topic: str | None = Field(default=None, description="关联热点话题")
    risk_flags: list[str] = Field(
        default_factory=list,
        description="风险标签，如 political、ad",
    )
    review_status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="人工审核状态",
    )


class ImageFeed(BaseModel):
    """一次多源聚合结果。"""

    model_config = ConfigDict(extra="forbid")

    items: list[ImageItem] = Field(default_factory=list, description="去重排序后的图片项")
    fetched_at: datetime = Field(description="聚合完成时间")
    providers_ok: list[str] = Field(
        default_factory=list,
        description="本次成功返回内容的来源",
    )
    providers_failed: list[str] = Field(
        default_factory=list,
        description="本次失败或未实现的来源",
    )


class SourceConfigBase(BaseModel):
    """单个来源的公共配置。"""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(default=True, description="是否启用该来源")
    limit: int = Field(default=20, description="单次请求最大条数")
    timeout: float = Field(default=5.0, description="请求超时秒数")
    allow_nsfw: bool = Field(default=False, description="是否允许 NSFW 内容")
    media_types: list[MediaType] = Field(
        default_factory=lambda: [MediaType.IMAGE, MediaType.GIF],
        description="允许的媒体类型",
    )
    min_score: float | None = Field(default=None, description="最低热度分数")
    api_key: str | None = Field(default=None, description="来源 API key")


class FetchPolicy(BaseModel):
    """多源并发与聚合默认策略。"""

    model_config = ConfigDict(extra="forbid")

    per_source_timeout: float = Field(default=5.0, description="单源超时秒数")
    per_source_limit: int = Field(default=20, description="单源最大条数")
    total_limit: int = Field(default=50, description="聚合后最大返回条数")
    retries: int = Field(default=1, description="单源失败重试次数")
    skip_failed_providers: bool = Field(
        default=True,
        description="单源失败时是否跳过并继续其它源",
    )


class HotMemeModels(BaseModel):
    """HotMeme 根配置（可由 YAML/JSON 载入）。"""

    model_config = ConfigDict(extra="ignore")

    cn: "CnSourcesConfig | None" = Field(
        default=None,
        description="中国热点与图文源配置",
    )
    fetch: FetchPolicy = Field(default_factory=FetchPolicy)
    cn_pipeline: "CnPipelinePolicy | None" = Field(
        default=None,
        description="中国源发现→搜图管线策略",
    )
