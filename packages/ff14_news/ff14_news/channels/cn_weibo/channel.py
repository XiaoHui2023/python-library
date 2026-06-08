from datetime import datetime, timezone
from pathlib import Path

from ff14_news.channels.cn_weibo.account_resolve import is_official_account_key
from ff14_news.channels.cn_weibo.constants import (
    CHANNEL_ID,
    DEFAULT_UID,
    DISPLAY_NAME,
    MOBILE_ORIGIN,
    SCREEN_NAME,
)
from ff14_news.channels.cn_weibo.crawl_backend import WeiboCrawlBackend
from ff14_news.channels.cn_weibo.post_adapter import post_to_article, post_to_list_item
from ff14_news.common.list_feed import article_from_list_item
from ff14_news.models import NewsArticle, NewsFeed, NewsListItem

_TIMELINE_SCAN_PAGE_SIZE = 20
_TIMELINE_SCAN_MAX_PAGES = 30
_LIST_ORIGINAL_MAX_PAGES = 10


class CnWeiboChannel:
    """FF14 官方微博（m.weibo.cn 时间线，crawl4weibo + Playwright 过反爬）。

    默认抓取列表级字段；长文正文块须 fetch_article_detail。
    """

    channel_id = CHANNEL_ID
    display_name = DISPLAY_NAME

    def __init__(
        self,
        *,
        screen_name: str = SCREEN_NAME,
        uid: str | None = None,
        cookie: str | None = None,
        cookie_storage_path: Path | None = None,
        browser_headless: bool = True,
        timeout_seconds: float = 60.0,
    ) -> None:
        """绑定微博账号。

        Args:
            screen_name: 微博账号标识，默认 cnff14；也接受显示名「最终幻想14」
            uid: 已知 numeric uid 时可省略解析；官方账号默认 DEFAULT_UID
            cookie: 浏览器 m.weibo.cn Cookie 整串；省略时用 Playwright 自动获取
            cookie_storage_path: Playwright 会话缓存，便于复用 Cookie
            browser_headless: 自动取 Cookie 时是否无头运行浏览器
            timeout_seconds: 保留参数，与 crawl4weibo 内部超时一致
        """
        self.screen_name = screen_name
        self._timeout = timeout_seconds
        self._backend = WeiboCrawlBackend(
            cookie=cookie,
            cookie_storage_path=cookie_storage_path,
            browser_headless=browser_headless,
        )
        if uid is not None:
            self._uid = str(uid).strip()
        elif is_official_account_key(screen_name):
            self._uid = DEFAULT_UID
        else:
            self._uid = self._backend.resolve_screen_name(screen_name)
    @property
    def uid(self) -> str:
        return self._uid

    def list_items(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> list[NewsListItem]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        return self._collect_original_list_items(
            limit=limit,
            start_page=page_index + 1,
        )

    def fetch_article_detail(self, article_id: str) -> NewsArticle:
        article_id = str(article_id).strip()
        if not article_id:
            raise ValueError("article_id must not be empty")
        post = self._backend.fetch_post_detail(article_id)
        return post_to_article(post, channel_id=self.channel_id)

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
        articles = [
            self._article_list_level_by_id(str(aid).strip()) for aid in article_ids
        ]
        return self._build_feed(articles)

    def _article_list_level_by_id(self, article_id: str) -> NewsArticle:
        item = self._find_list_item_by_id(article_id)
        if item is not None:
            return article_from_list_item(item)
        post = self._backend.fetch_post(article_id)
        return article_from_list_item(
            post_to_list_item(post, channel_id=self.channel_id)
        )

    def _collect_original_list_items(
        self,
        *,
        limit: int,
        start_page: int,
    ) -> list[NewsListItem]:
        items: list[NewsListItem] = []
        page = start_page
        last_page = start_page + _LIST_ORIGINAL_MAX_PAGES - 1
        while len(items) < limit and page <= last_page:
            posts = self._backend.fetch_timeline_posts(self._uid, page=page)
            if not posts:
                break
            for post in posts:
                if post.retweeted_status is not None:
                    continue
                if post.user_id and post.user_id != self._uid:
                    continue
                items.append(post_to_list_item(post, channel_id=self.channel_id))
                if len(items) >= limit:
                    return items
            if len(posts) < _TIMELINE_SCAN_PAGE_SIZE:
                break
            page += 1
        return items

    def _find_list_item_by_id(self, article_id: str) -> NewsListItem | None:
        for page_index in range(_TIMELINE_SCAN_MAX_PAGES):
            items = self.list_items(
                limit=_TIMELINE_SCAN_PAGE_SIZE,
                page_index=page_index,
            )
            for item in items:
                if item.id == article_id:
                    return item
            if len(items) < _TIMELINE_SCAN_PAGE_SIZE:
                break
        return None

    def _build_feed(self, articles: list[NewsArticle]) -> NewsFeed:
        return NewsFeed(
            channel_id=self.channel_id,
            source_list_url=f"{MOBILE_ORIGIN}/u/{self._uid}",
            category_code=None,
            fetched_at=datetime.now(timezone.utc),
            articles=articles,
        )
