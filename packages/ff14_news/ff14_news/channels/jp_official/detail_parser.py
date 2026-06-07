import html
import re
from datetime import datetime, timezone

from ff14_news.channels.jp_official.constants import DETAIL_URL_TEMPLATE, SITE_ORIGIN
from ff14_news.common.html_blocks import html_to_blocks
from ff14_news.models import NewsArticle, NewsContentBlock

_WRAPPER_RE = re.compile(
    r'<div class="news__detail__wrapper">(.*?)</div>\s*<div class="news__detail__social">',
    re.DOTALL,
)
_TITLE_RE = re.compile(
    r'<article class="news__detail">.*?<h1>([^<]+)</h1>',
    re.DOTALL,
)
_TIMESTAMP_RE = re.compile(
    r'<article class="news__detail">.*?ldst_strftime\((\d+),',
    re.DOTALL,
)
_FIRST_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"')


def parse_detail_metadata(
    page_html: str,
    article_id: str,
    *,
    channel_id: str,
) -> NewsArticle:
    """详情页元数据：标题、时间、头图、摘要，不解析正文块。"""
    title_match = _TITLE_RE.search(page_html)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""

    ts_match = _TIMESTAMP_RE.search(page_html)
    if ts_match:
        publish_date = datetime.fromtimestamp(
            int(ts_match.group(1)),
            tz=timezone.utc,
        )
    else:
        publish_date = datetime.fromtimestamp(0, tz=timezone.utc)

    wrapper_match = _WRAPPER_RE.search(page_html)
    wrapper_html = wrapper_match.group(1) if wrapper_match else ""
    cover_url = _first_image_url(wrapper_html)
    summary = _plain_summary_from_html(wrapper_html)

    return NewsArticle(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=publish_date,
        summary=summary,
        category_code=None,
        cover_image_url=cover_url,
        source_page_url=DETAIL_URL_TEMPLATE.format(article_id=article_id),
        blocks=[],
    )


def parse_detail_page(
    page_html: str,
    article_id: str,
    *,
    channel_id: str,
) -> NewsArticle:
    title_match = _TITLE_RE.search(page_html)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""

    ts_match = _TIMESTAMP_RE.search(page_html)
    if ts_match:
        publish_date = datetime.fromtimestamp(
            int(ts_match.group(1)),
            tz=timezone.utc,
        )
    else:
        publish_date = datetime.fromtimestamp(0, tz=timezone.utc)

    wrapper_match = _WRAPPER_RE.search(page_html)
    wrapper_html = wrapper_match.group(1) if wrapper_match else ""
    blocks = html_to_blocks(wrapper_html, base_url=SITE_ORIGIN)

    cover_url = _first_image_url(wrapper_html)
    summary = _summary_from_blocks(blocks)

    return NewsArticle(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=publish_date,
        summary=summary,
        category_code=None,
        cover_image_url=cover_url,
        source_page_url=DETAIL_URL_TEMPLATE.format(article_id=article_id),
        blocks=blocks,
    )


def _first_image_url(wrapper_html: str) -> str | None:
    match = _FIRST_IMG_RE.search(wrapper_html)
    if not match:
        return None
    url = match.group(1).strip()
    return url or None


_TAG_RE = re.compile(r"<[^>]+>")


def _plain_summary_from_html(wrapper_html: str, max_len: int = 200) -> str:
    text = _TAG_RE.sub(" ", wrapper_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _summary_from_blocks(blocks: list[NewsContentBlock], max_len: int = 200) -> str:
    for block in blocks:
        if block.text and block.text.strip():
            text = block.text.strip()
            if len(text) <= max_len:
                return text
            return text[: max_len - 1] + "…"
    return ""
