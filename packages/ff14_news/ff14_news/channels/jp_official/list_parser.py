import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from ff14_news.channels.jp_official.constants import DETAIL_URL_TEMPLATE
from ff14_news.models import NewsListItem

_SUMMARY_MAX_LEN = 200
_TAG_RE = re.compile(r"<[^>]+>")
_DETAIL_ID_RE = re.compile(r"/lodestone/topics/detail/([a-f0-9]+)/?")
_BANNER_RE = re.compile(
    r'<div class="news__list--banner">(.*?)</div>\s*(?=</li>|<header)',
    re.DOTALL,
)
_TITLE_RE = re.compile(
    r'class="news__list--title"[^>]*>\s*<a[^>]*>([^<]+)</a>',
    re.DOTALL,
)
_TIMESTAMP_RE = re.compile(r"ldst_strftime\((\d+),")
_COVER_RE = re.compile(
    r'class="news__list--img"[^>]*>\s*<img[^>]+src="([^"]+)"',
    re.DOTALL,
)
_ITEM_SPLIT_RE = re.compile(r'<li class="news__list--topics[^"]*">')


@dataclass(frozen=True)
class TopicsListRow:
    article_id: str
    title: str
    publish_date: datetime
    summary: str
    cover_image_url: str | None


def topics_list_url(page_index: int) -> str:
    from ff14_news.channels.jp_official.constants import TOPICS_LIST_URL

    if page_index <= 0:
        return TOPICS_LIST_URL
    return f"{TOPICS_LIST_URL}?page={page_index + 1}"


def parse_topics_list_page(html: str, *, limit: int) -> list[TopicsListRow]:
    fragments = _ITEM_SPLIT_RE.split(html)
    rows: list[TopicsListRow] = []
    for fragment in fragments[1:]:
        row = _parse_item_fragment(fragment)
        if row is not None:
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def list_row_to_item(row: TopicsListRow, *, channel_id: str) -> NewsListItem:
    return NewsListItem(
        channel_id=channel_id,
        id=row.article_id,
        title=row.title,
        publish_date=row.publish_date,
        summary=row.summary,
        cover_image_url=row.cover_image_url,
        source_page_url=DETAIL_URL_TEMPLATE.format(article_id=row.article_id),
    )


def _parse_item_fragment(fragment: str) -> TopicsListRow | None:
    id_match = _DETAIL_ID_RE.search(fragment)
    if not id_match:
        return None
    article_id = id_match.group(1)

    title_match = _TITLE_RE.search(fragment)
    title = html.unescape(title_match.group(1).strip()) if title_match else ""

    ts_match = _TIMESTAMP_RE.search(fragment)
    if ts_match:
        publish_date = datetime.fromtimestamp(
            int(ts_match.group(1)),
            tz=timezone.utc,
        )
    else:
        publish_date = datetime.fromtimestamp(0, tz=timezone.utc)

    cover_match = _COVER_RE.search(fragment)
    cover = cover_match.group(1).strip() if cover_match else None
    summary = _banner_plain_summary(fragment)

    return TopicsListRow(
        article_id=article_id,
        title=title,
        publish_date=publish_date,
        summary=summary,
        cover_image_url=cover,
    )


def _banner_plain_summary(fragment: str) -> str:
    match = _BANNER_RE.search(fragment)
    if not match:
        return ""
    inner = re.sub(r"<img[^>]*>", " ", match.group(1), flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", inner)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if len(text) <= _SUMMARY_MAX_LEN:
        return text
    return text[: _SUMMARY_MAX_LEN - 1] + "…"
