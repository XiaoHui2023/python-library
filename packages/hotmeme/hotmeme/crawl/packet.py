from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.cn_models import TopicItem
from hotmeme.models import ImageItem


class HotMemeCrawlPacket(BaseModel):
    """单次爬取数据包：供 ``crawl_once`` 与自动轮询回调共用。"""

    model_config = ConfigDict(extra="forbid")

    crawled_at: datetime = Field(description="爬取完成时间")
    new_items: list[ImageItem] = Field(
        default_factory=list,
        description="相对上次爬取新增的图片项",
    )
    new_topics: list[TopicItem] = Field(
        default_factory=list,
        description="相对上次爬取新增的热点项",
    )
    fetched_items: list[ImageItem] = Field(
        default_factory=list,
        description="本轮各源拉取到的全部图片项（含已见过）",
    )
    fetched_topics: list[TopicItem] = Field(
        default_factory=list,
        description="本轮拉取到的全部热点项（含已见过）",
    )
    providers_ok: list[str] = Field(default_factory=list, description="成功的来源")
    providers_failed: list[str] = Field(default_factory=list, description="失败的来源")
    is_initial: bool = Field(
        default=False,
        description="是否为实例创建后的首次爬取",
    )
