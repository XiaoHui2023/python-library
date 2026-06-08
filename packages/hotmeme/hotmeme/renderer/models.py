from __future__ import annotations



from datetime import datetime

from enum import StrEnum



from pydantic import BaseModel, ConfigDict, Field





class OutputMediaKind(StrEnum):

    """输出包媒体种类。"""



    IMAGE = "image"

    VIDEO = "video"





class MemeOutputPacket(BaseModel):

    """可交付的热帖输出包：媒体地址 + 文案 + 分析字段。"""



    model_config = ConfigDict(extra="forbid")



    item_id: str = Field(description="对应 ImageItem.id")

    platform: str = Field(description="来源平台")

    search_tag: str | None = Field(default=None, description="拉取时使用的搜索话题 tag")

    provider: str = Field(description="内容源，如 tikhub")

    source_id: str = Field(description="来源侧原始 ID")

    title: str = Field(description="主标题")

    caption: str = Field(description="展示用文案，可含作者")

    media_type: str = Field(description="原始媒体类型，如 image / video")

    media_kind: OutputMediaKind = Field(description="输出主媒体种类")

    media_url: str = Field(description="主媒体地址（图或视频）")

    image_url: str = Field(default="", description="图片或封面直链")

    video_url: str | None = Field(default=None, description="视频直链")

    thumbnail_url: str | None = Field(default=None, description="缩略图或封面")

    source_url: str = Field(description="原帖链接")

    author: str | None = Field(default=None, description="作者名")

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

