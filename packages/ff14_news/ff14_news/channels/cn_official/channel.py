from datetime import datetime, timezone

from ff14_news.channels.cn_official.constants import (
    CHANNEL_ID,
    DISPLAY_NAME,
    NEWS_LIST_CATEGORY_CODE,
    OFFICIAL_NEWS_DETAIL_URL_TEMPLATE,
    OFFICIAL_NEWS_LIST_URL,
)
from ff14_news.channels.cn_official.cqnews_client import CqNewsClient, parse_publish_date
from ff14_news.channels.cn_official.html_content import html_to_blocks
from ff14_news.common.list_feed import article_from_list_item
from ff14_news.models import NewsArticle, NewsFeed, NewsListItem


class CnOfficialChannel:
    """FF14 国服官网新闻（ff.web.sdo.com / cqnews）。

    默认抓取与旧 Selenium 列表一致：头图、标题、摘要、详情页链接。
    正文块须显式调用 fetch_article_detail。
    """

    channel_id = CHANNEL_ID
    display_name = DISPLAY_NAME

    def __init__(
        self,
        *,
        category_code: int = NEWS_LIST_CATEGORY_CODE,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.category_code = category_code
        self._client = CqNewsClient(timeout_seconds=timeout_seconds)

    def list_items(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> list[NewsListItem]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        items, _total = self._client.fetch_list_page(
            self.category_code,
            page_index,
            limit,
        )
        return items[:limit]

    def fetch_article_detail(self, article_id: str) -> NewsArticle:
        return self._detail_to_article(self._client.fetch_detail_raw(article_id))

    def fetch_article(self, article_id: str) -> NewsArticle:
        return self.fetch_article_detail(article_id)

    def fetch_articles(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> NewsFeed:
        items = self.list_items(limit=limit, page_index=page_index)
        articles = [
            article_from_list_item(item, category_code=self.category_code)
            for item in items
        ]
        return self._build_feed(articles)

    def fetch_articles_by_ids(self, article_ids: list[str]) -> NewsFeed:
        if not article_ids:
            raise ValueError("article_ids must not be empty")
        articles = [
            self._detail_to_list_article(self._client.fetch_detail_raw(aid))
            for aid in article_ids
        ]
        return self._build_feed(articles)

    def _detail_to_list_article(self, data: dict) -> NewsArticle:
        article_id = str(int(data["Id"]))
        cover = data.get("HomeImagePath")
        cover_url = str(cover).strip() if cover else None
        if cover_url == "":
            cover_url = None
        publish_raw = str(data.get("PublishDate") or "")
        return NewsArticle(
            channel_id=self.channel_id,
            id=article_id,
            title=str(data.get("Title") or ""),
            publish_date=parse_publish_date(publish_raw),
            summary=str(data.get("Summary") or ""),
            category_code=int(data.get("CategoryCode") or self.category_code),
            cover_image_url=cover_url,
            source_page_url=OFFICIAL_NEWS_DETAIL_URL_TEMPLATE.format(
                article_id=article_id
            ),
            blocks=[],
        )

    def _detail_to_article(self, data: dict) -> NewsArticle:
        article = self._detail_to_list_article(data)
        html = str(data.get("Content") or "")
        blocks = html_to_blocks(html)
        return article.model_copy(update={"blocks": blocks})

    def _build_feed(self, articles: list[NewsArticle]) -> NewsFeed:
        return NewsFeed(
            channel_id=self.channel_id,
            source_list_url=OFFICIAL_NEWS_LIST_URL,
            category_code=self.category_code,
            fetched_at=datetime.now(timezone.utc),
            articles=articles,
        )
