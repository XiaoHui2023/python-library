from __future__ import annotations

from datetime import datetime, timezone

from crawl4weibo.models.post import Post

from ff14_news.channels.cn_weibo.constants import (
    DETAIL_URL_TEMPLATE,
    PERMALINK_TEMPLATE,
)
from ff14_news.channels.cn_weibo.mblog_parser import (
    _SUMMARY_MAX_LEN,
    _TITLE_MAX_LEN,
    _FULL_TEXT_RE,
)
from ff14_news.models import NewsArticle, NewsBlockType, NewsContentBlock, NewsListItem


def post_to_list_item(post: Post, *, channel_id: str) -> NewsListItem:
    """将 crawl4weibo Post 转为列表级 NewsListItem。"""
    effective = _effective_post(post)
    article_id = str(post.id).strip()
    title = _title_from_plain(effective.text)
    summary = _summary_from_plain(effective.text)
    cover = effective.pic_urls[0] if effective.pic_urls else None
    return NewsListItem(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=_publish_date(post.created_at),
        summary=summary,
        cover_image_url=cover,
        source_page_url=DETAIL_URL_TEMPLATE.format(article_id=article_id),
    )


def post_to_article(post: Post, *, channel_id: str) -> NewsArticle:
    """将 crawl4weibo Post 转为含正文块的 NewsArticle。"""
    effective = _effective_post(post)
    article_id = str(post.id).strip()
    blocks = _blocks_from_post(effective)
    title = _title_from_plain(effective.text)
    summary = _summary_from_blocks(blocks) or _summary_from_plain(effective.text)
    cover = effective.pic_urls[0] if effective.pic_urls else None
    return NewsArticle(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=_publish_date(post.created_at),
        summary=summary,
        category_code=None,
        cover_image_url=cover,
        source_page_url=PERMALINK_TEMPLATE.format(article_id=article_id),
        blocks=blocks,
    )


def _effective_post(post: Post) -> Post:
    if post.retweeted_status is not None:
        return post.retweeted_status
    return post


def _publish_date(value: datetime | None) -> datetime:
    if value is None:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _title_from_plain(text: str) -> str:
    first_line = text.strip().split("\n", 1)[0].strip()
    if not first_line:
        return "微博"
    if len(first_line) <= _TITLE_MAX_LEN:
        return first_line
    return first_line[: _TITLE_MAX_LEN - 1] + "…"


def _summary_from_plain(text: str) -> str:
    plain = _FULL_TEXT_RE.sub("", text.strip()).strip()
    if len(plain) <= _SUMMARY_MAX_LEN:
        return plain
    return plain[: _SUMMARY_MAX_LEN - 1] + "…"


def _summary_from_blocks(blocks: list[NewsContentBlock]) -> str:
    for block in blocks:
        if block.text and block.text.strip():
            snippet = block.text.strip()
            if len(snippet) <= _SUMMARY_MAX_LEN:
                return snippet
            return snippet[: _SUMMARY_MAX_LEN - 1] + "…"
    return ""


def _blocks_from_post(post: Post) -> list[NewsContentBlock]:
    blocks: list[NewsContentBlock] = []
    text = post.text.strip()
    if text:
        blocks.append(NewsContentBlock(type=NewsBlockType.TEXT, text=text))
    for url in post.pic_urls:
        blocks.append(NewsContentBlock(type=NewsBlockType.IMAGE, url=url))
    return blocks
