from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class NewsBlockType(StrEnum):
    """正文块类型。"""

    TEXT = "text"
    HEADING = "heading"
    IMAGE = "image"


class NewsContentBlock(BaseModel):
    """单条有序正文块：纯文本、标题或图片。"""

    type: NewsBlockType = Field(description="块类型")
    text: str | None = Field(default=None, description="文本或标题内容")
    url: str | None = Field(default=None, description="图片绝对地址")
    level: int | None = Field(default=None, description="标题级别，1–6")


class NewsArticle(BaseModel):
    """一篇新闻。

    默认 fetch_articles / fetch_articles_by_ids 仅填充列表级字段，blocks 为空。
    正文块须通过各渠道 fetch_article_detail 拉取。
    """

    channel_id: str = Field(description="渠道标识，如 cn_official")
    id: str = Field(description="渠道内文章 ID")
    title: str = Field(description="标题")
    publish_date: datetime = Field(description="发布时间")
    summary: str = Field(default="", description="摘要")
    category_code: int | None = Field(
        default=None,
        description="栏目编号；仅部分渠道有（如国服 cqnews）",
    )
    cover_image_url: str | None = Field(default=None, description="列表头图")
    source_page_url: str = Field(description="官网详情页 hash 链接")
    blocks: list[NewsContentBlock] = Field(
        default_factory=list,
        description="按阅读顺序排列的正文块",
    )


class NewsFeed(BaseModel):
    """一次抓取结果：列表顺序与对应渠道新闻列表一致。"""

    channel_id: str = Field(description="渠道标识，如 cn_official")
    source_list_url: str = Field(description="列表页地址")
    category_code: int | None = Field(
        default=None,
        description="列表栏目编号；仅部分渠道有",
    )
    fetched_at: datetime = Field(description="抓取完成时间")
    articles: list[NewsArticle] = Field(
        default_factory=list,
        description="文章列表，顺序与列表 API 返回一致",
    )


class NewsChannelFetchError(BaseModel):
    """单渠道抓取失败记录。"""

    channel_id: str = Field(description="渠道标识")
    message: str = Field(description="失败原因")


class NewsFeedBundle(BaseModel):
    """已启用渠道的并行抓取结果。"""

    fetched_at: datetime = Field(description="整包抓取完成时间")
    feeds: dict[str, NewsFeed] = Field(
        default_factory=dict,
        description="按 channel_id 索引的成功 feed",
    )
    errors: list[NewsChannelFetchError] = Field(
        default_factory=list,
        description="失败渠道及原因",
    )


class NewsListItem(BaseModel):
    """列表项元数据（未展开正文）。"""

    channel_id: str = Field(description="渠道标识，如 cn_official")
    id: str = Field(description="文章 ID")
    title: str = Field(description="标题")
    publish_date: datetime = Field(description="发布时间")
    summary: str = Field(default="", description="摘要")
    cover_image_url: str | None = Field(default=None, description="头图")
    source_page_url: str = Field(description="官网详情页链接")
