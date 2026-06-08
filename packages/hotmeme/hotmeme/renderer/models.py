from __future__ import annotations

from datetime import datetime

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.models import PostProcessStageStat
from hotmeme.renderer.content import PostContent, PostReference


class OutputMediaKind(StrEnum):
    """输出包媒体种类。"""

    IMAGE = "image"
    VIDEO = "video"


class MemeOutputPacket(BaseModel):
    """一条可对外发送的热帖消息：``content`` 内多图与正文同属本条，勿拆成多条。"""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(description="对应 ImageItem.id")
    platform: str = Field(description="来源平台")
    provider: str = Field(description="内容源，如 tikhub")
    source_id: str = Field(description="来源侧原始 ID")
    title: str = Field(description="标题摘要，便于列表索引")
    content: PostContent = Field(description="按帖子顺序排好的图文内容")
    reference: PostReference = Field(description="作者与原帖链等参考信息")
    media_type: str = Field(description="原始媒体类型，如 image / video")
    media_kind: OutputMediaKind = Field(description="输出主媒体种类")
    media_url: str = Field(description="主媒体远程地址；图片帖为首张图源 URL")
    image_url: str = Field(default="", description="首张图片远程 URL")
    video_url: str | None = Field(default=None, description="视频直链")
    thumbnail_url: str | None = Field(default=None, description="缩略图或封面")
    score: float | None = Field(default=None, description="平台互动热度")
    rank_score: float | None = Field(default=None, description="本地排序分")
    created_at: datetime | None = Field(default=None, description="发布时间")
    nsfw: bool = Field(default=False, description="是否 NSFW")
    risk_flags: list[str] = Field(default_factory=list, description="风险标签")
    api_filters: str = Field(default="", description="拉取层 API/来源筛选说明")
    post_filters: str = Field(default="", description="已通过的后处理阶段")


class MemeOutputBatch(BaseModel):
    """一批渲染结果。"""

    model_config = ConfigDict(extra="forbid")

    packets: list[MemeOutputPacket] = Field(default_factory=list)
    rendered_at: datetime = Field(description="渲染完成时间")
    materialize_errors: list[str] = Field(
        default_factory=list,
        description="渲染前图片下载失败说明",
    )
    materialize_stage: PostProcessStageStat | None = Field(
        default=None,
        description="渲染前图片下载阶段统计",
    )
