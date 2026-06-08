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
]

DEFAULT_XHS_SEARCH_TAGS: tuple[str, ...] = (
    "搞笑日常",
)


class TikHubApiCall(BaseModel):
    """单次 TikHub HTTP 请求记录。"""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(description="HTTP 方法")
    path: str = Field(description="API 路径")
    params: dict[str, Any] | None = Field(default=None, description="查询或 JSON 体参数摘要")


class ImageBlob(BaseModel):
    """单张已下载图片的二进制载荷。"""

    model_config = ConfigDict(extra="forbid")

    data: bytes = Field(description="图片二进制数据")
    content_type: str | None = Field(
        default=None,
        description="MIME 类型，如 image/jpeg",
    )


class ImageItem(BaseModel):
    """统一热帖项：图文或短视频帖。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="库内唯一 ID")
    provider: str = Field(description="来源名称，如 tikhub")
    source_id: str = Field(description="来源侧原始 ID")
    title: str = Field(description="标题或短描述")
    body: str | None = Field(default=None, description="正文 desc，与 title 分列时供排版合并")
    image_urls: list[str] = Field(
        default_factory=list,
        description="笔记图片 URL 列表，按图集顺序",
    )
    image_blobs: list[ImageBlob] = Field(
        default_factory=list,
        description="已下载图片二进制，顺序与 image_urls 一致",
    )
    image_url: str = Field(
        default="",
        description="主图远程 URL",
    )
    video_url: str | None = Field(default=None, description="可播放视频地址")
    preview_url: str | None = Field(default=None, description="预览小图地址")
    source_url: str = Field(description="原始页面或帖子链接")
    author: str | None = Field(default=None, description="作者名")
    community: str | None = Field(default=None, description="平台或频道标识")
    search_tag: str | None = Field(
        default=None,
        description="拉取时使用的搜索话题 tag（如小红书 #搞笑日常# 的「搞笑日常」）",
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


class PostProcessStageStat(BaseModel):
    """单步后处理进出条数。"""

    model_config = ConfigDict(extra="forbid")

    stage: str = Field(description="阶段名")
    in_count: int = Field(description="进入条数")
    out_count: int = Field(description="离开条数")
    dropped: int = Field(description="丢弃条数")


class XhsKeywordFetchStat(BaseModel):
    """单次小红书 tag 搜索的解析统计。"""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(description="搜索关键词，如 #搞笑日常#")
    search_tag: str = Field(description="话题 tag 名")
    api_list_items: int = Field(description="响应 data.items 列表长度")
    note_candidates: int = Field(description="识别到的笔记卡片数")
    parsed_with_media: int = Field(description="解析出可展示媒体的条数")
    no_media: int = Field(description="有笔记但无封面/视频 URL")
    tag_dedup_skipped: int = Field(description="跨 tag 合并时因 note id 重复跳过")
    merged_items: int = Field(description="本 keyword 新并入条数")


class FetchDiagnostics(BaseModel):
    """一轮拉取：解析与过滤诊断。"""

    model_config = ConfigDict(extra="forbid")

    parsed_before_filter: int = Field(default=0, description="进入 post_process 前条数")
    final_count: int = Field(default=0, description="post_process 后条数")
    xhs_keywords: list[XhsKeywordFetchStat] = Field(default_factory=list)
    post_process: list[PostProcessStageStat] = Field(default_factory=list)


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
        ],
        description="允许的媒体类型（默认仅图文）",
    )
    api_key: str | None = Field(default=None, description="API key")


class TikHubConfig(SourceConfigBase):
    """TikHub 热帖拉取配置。"""


class XiaohongshuPolicy(BaseModel):
    """小红书按话题 tag 搜索策略。"""

    model_config = ConfigDict(extra="forbid")

    search_tags: list[str] = Field(
        default_factory=lambda: list(DEFAULT_XHS_SEARCH_TAGS),
        description="话题 tag 列表，按命中率从高到低排列",
    )
    page: int = Field(default=1, ge=1, description="搜索页码，从 1 开始")
    sort_type: str = Field(
        default="general",
        description="排序：general（综合）、popularity_descending（最多点赞）、time_descending 等",
    )
    time_filter: str = Field(
        default="一天内",
        description="发布时间：不限、一天内、一周内、半年内",
    )
    note_type: str = Field(
        default="普通笔记",
        description="笔记类型：普通笔记（图文）、视频笔记、不限",
    )
    min_score: float = Field(
        default=500.0,
        description="互动分须大于该值才保留（点赞+评论+收藏+分享合计）",
    )

    def search_keywords(self) -> list[str]:
        """本轮实际用于搜索的 ``#话题#`` 关键词列表。"""
        from hotmeme.sources.parsers.xiaohongshu import format_xhs_tag_query

        keywords: list[str] = []
        for tag in self.search_tags:
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


class AssetsPolicy(BaseModel):
    """图片内存下载策略。"""

    model_config = ConfigDict(extra="forbid")

    download: bool = Field(
        default=True,
        description="为 true 时拉取后下载全部图片到内存，失败则丢弃该帖并记入 fetch_errors",
    )
    timeout: float = Field(default=30.0, description="单张图片下载超时秒数")
    max_images_per_item: int | None = Field(
        default=3,
        ge=1,
        description="每帖最多下载前 N 张图；与 content 中图片块上限一致；null 表示不限制",
    )
    download_workers: int = Field(
        default=4,
        ge=1,
        le=32,
        description="单帖内并行下载图片的线程数",
    )
    min_bytes: int = Field(
        default=256,
        ge=1,
        description="接受的最小文件体积；过小视为无效响应",
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
    assets: AssetsPolicy = Field(default_factory=AssetsPolicy)
    fetch: FetchPolicy = Field(default_factory=FetchPolicy)


def default_pipeline() -> PipelinePolicy:
    return PipelinePolicy()
