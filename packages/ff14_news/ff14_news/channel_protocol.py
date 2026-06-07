from typing import Protocol, runtime_checkable

from ff14_news.models import NewsArticle, NewsFeed, NewsListItem


@runtime_checkable
class NewsChannel(Protocol):
    """新闻渠道：各渠道独立实现，输出统一的 Feed / Article 结构。"""

    channel_id: str
    display_name: str

    def list_items(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> list[NewsListItem]:
        """拉取列表元数据，顺序与对应站点列表一致。"""
        ...

    def fetch_article_detail(self, article_id: str) -> NewsArticle:
        """拉取单篇详情并解析正文块（blocks 非空）。"""
        ...

    def fetch_article(self, article_id: str) -> NewsArticle:
        """拉取单篇详情；与 fetch_article_detail 相同。"""
        ...

    def fetch_articles(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> NewsFeed:
        """按列表顺序抓取列表级字段（标题、摘要、头图、链接），blocks 为空。"""
        ...

    def fetch_articles_by_ids(self, article_ids: list[str]) -> NewsFeed:
        """按给定 ID 顺序抓取列表级字段，不展开正文块。"""
        ...
