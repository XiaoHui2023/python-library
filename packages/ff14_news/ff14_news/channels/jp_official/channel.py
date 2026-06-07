from datetime import datetime, timezone

from ff14_news.channels.jp_official.constants import (
    CHANNEL_ID,
    DETAIL_URL_TEMPLATE,
    DISPLAY_NAME,
    TOPICS_LIST_URL,
)
from ff14_news.channels.jp_official.detail_parser import (
    parse_detail_metadata,
    parse_detail_page,
)
from ff14_news.channels.jp_official.http_client import fetch_html
from ff14_news.channels.jp_official.list_parser import (
    list_row_to_item,
    parse_topics_list_page,
    topics_list_url,
)
from ff14_news.common.list_feed import article_from_list_item
from ff14_news.models import NewsArticle, NewsFeed, NewsListItem

_LIST_SCAN_PAGE_SIZE = 30
_LIST_SCAN_MAX_PAGES = 20


class JpOfficialChannel:
    """FF14 日文官网 Lodestone トピックス。

    默认抓取列表级字段（含 news__list--banner 摘要）；正文块须 fetch_article_detail。
    """

    channel_id = CHANNEL_ID
    display_name = DISPLAY_NAME

    def __init__(self, *, timeout_seconds: float = 120.0) -> None:
        self._timeout = timeout_seconds

    def list_items(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> list[NewsListItem]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        url = topics_list_url(page_index)
        html = fetch_html(url, timeout_seconds=self._timeout)
        rows = parse_topics_list_page(html, limit=limit)
        return [list_row_to_item(row, channel_id=self.channel_id) for row in rows]

    def fetch_article_detail(self, article_id: str) -> NewsArticle:
        article_id = str(article_id).strip()
        if not article_id:
            raise ValueError("article_id must not be empty")
        url = DETAIL_URL_TEMPLATE.format(article_id=article_id)
        html = fetch_html(url, timeout_seconds=self._timeout)
        return parse_detail_page(html, article_id, channel_id=self.channel_id)

    def fetch_article(self, article_id: str) -> NewsArticle:
        return self.fetch_article_detail(article_id)

    def fetch_articles(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> NewsFeed:
        items = self.list_items(limit=limit, page_index=page_index)
        articles = [article_from_list_item(item) for item in items]
        return self._build_feed(articles)

    def fetch_articles_by_ids(self, article_ids: list[str]) -> NewsFeed:
        if not article_ids:
            raise ValueError("article_ids must not be empty")
        wanted = {str(aid).strip() for aid in article_ids}
        found: dict[str, NewsArticle] = {}
        for page_index in range(_LIST_SCAN_MAX_PAGES):
            if wanted.issubset(found):
                break
            items = self.list_items(
                limit=_LIST_SCAN_PAGE_SIZE,
                page_index=page_index,
            )
            if not items:
                break
            for item in items:
                if item.id in wanted and item.id not in found:
                    found[item.id] = article_from_list_item(item)
        articles: list[NewsArticle] = []
        for aid in article_ids:
            key = str(aid).strip()
            if key in found:
                articles.append(found[key])
            else:
                articles.append(self._metadata_from_detail(key))
        return self._build_feed(articles)

    def _metadata_from_detail(self, article_id: str) -> NewsArticle:
        url = DETAIL_URL_TEMPLATE.format(article_id=article_id)
        html = fetch_html(url, timeout_seconds=self._timeout)
        return parse_detail_metadata(html, article_id, channel_id=self.channel_id)

    def _build_feed(self, articles: list[NewsArticle]) -> NewsFeed:
        return NewsFeed(
            channel_id=self.channel_id,
            source_list_url=TOPICS_LIST_URL,
            category_code=None,
            fetched_at=datetime.now(timezone.utc),
            articles=articles,
        )
