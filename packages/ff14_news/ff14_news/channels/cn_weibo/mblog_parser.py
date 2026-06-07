import html
import re
from datetime import datetime

from ff14_news.channels.cn_weibo.constants import (
    DETAIL_URL_TEMPLATE,
    MOBILE_ORIGIN,
    PERMALINK_TEMPLATE,
)
from ff14_news.common.html_blocks import html_to_blocks
from ff14_news.models import NewsArticle, NewsBlockType, NewsContentBlock, NewsListItem

_TAG_RE = re.compile(r"<[^>]+>")
_FULL_TEXT_RE = re.compile(r"…?\.\.\.?全文\s*$|…全文\s*$")
_TITLE_MAX_LEN = 80
_SUMMARY_MAX_LEN = 200


def effective_mblog(mblog: dict) -> dict:
    """转发微博取内层原博；普通微博返回自身。"""
    inner = mblog.get("retweeted_status")
    if isinstance(inner, dict):
        return inner
    return mblog


def needs_detail_fetch(mblog: dict) -> bool:
    """正文被截断或标记长文时须拉 statuses/show。"""
    if mblog.get("isLongText"):
        return True
    raw = str(mblog.get("text") or "")
    plain = _plain_text(raw)
    if "全文" in raw and ("status" in raw or _FULL_TEXT_RE.search(plain)):
        return True
    return False


def mblog_id(mblog: dict) -> str:
    value = mblog.get("id") or mblog.get("mid") or mblog.get("bid")
    if not value:
        raise ValueError("mblog missing id")
    return str(value)


def parse_created_at(raw: str) -> datetime:
    text = (raw or "").strip()
    if not text:
        return datetime.fromtimestamp(0)
    try:
        return datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")
    except ValueError:
        return datetime.fromtimestamp(0)


def mblog_to_list_item(mblog: dict, *, channel_id: str) -> NewsListItem:
    article_id = mblog_id(mblog)
    effective = effective_mblog(mblog)
    title = _title_from_text(effective)
    summary = _summary_from_text(effective)
    cover = _first_pic_url(effective)
    return NewsListItem(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=parse_created_at(str(mblog.get("created_at") or "")),
        summary=summary,
        cover_image_url=cover,
        source_page_url=DETAIL_URL_TEMPLATE.format(article_id=article_id),
    )


def mblog_to_article(
    mblog: dict,
    *,
    channel_id: str,
) -> NewsArticle:
    article_id = mblog_id(mblog)
    effective = effective_mblog(mblog)
    blocks = blocks_from_mblog(mblog)
    title = _title_from_text(effective)
    summary = _summary_from_blocks(blocks) or _summary_from_text(effective)
    cover = _first_pic_url(effective)
    return NewsArticle(
        channel_id=channel_id,
        id=article_id,
        title=title,
        publish_date=parse_created_at(str(mblog.get("created_at") or "")),
        summary=summary,
        category_code=None,
        cover_image_url=cover,
        source_page_url=PERMALINK_TEMPLATE.format(article_id=article_id),
        blocks=blocks,
    )


def blocks_from_mblog(mblog: dict) -> list[NewsContentBlock]:
    effective = effective_mblog(mblog)
    text_html = str(effective.get("text") or "")
    wrapped = f"<div>{text_html}</div>" if text_html else ""
    blocks = html_to_blocks(wrapped, base_url=MOBILE_ORIGIN)
    for pic in effective.get("pics") or []:
        url = _pic_url(pic)
        if url:
            blocks.append(
                NewsContentBlock(type=NewsBlockType.IMAGE, url=url)
            )
    return blocks


def _plain_text(text_html: str) -> str:
    text = _TAG_RE.sub("", text_html)
    return html.unescape(text).replace("\xa0", " ").strip()


def _title_from_text(mblog: dict) -> str:
    plain = _plain_text(str(mblog.get("text") or ""))
    first_line = plain.split("\n", 1)[0].strip()
    if not first_line:
        return "微博"
    if len(first_line) <= _TITLE_MAX_LEN:
        return first_line
    return first_line[: _TITLE_MAX_LEN - 1] + "…"


def _summary_from_text(mblog: dict) -> str:
    plain = _plain_text(str(mblog.get("text") or ""))
    plain = _FULL_TEXT_RE.sub("", plain).strip()
    if len(plain) <= _SUMMARY_MAX_LEN:
        return plain
    return plain[: _SUMMARY_MAX_LEN - 1] + "…"


def _summary_from_blocks(blocks: list[NewsContentBlock]) -> str:
    for block in blocks:
        if block.text and block.text.strip():
            text = block.text.strip()
            if len(text) <= _SUMMARY_MAX_LEN:
                return text
            return text[: _SUMMARY_MAX_LEN - 1] + "…"
    return ""


def _first_pic_url(mblog: dict) -> str | None:
    pics = mblog.get("pics") or []
    if not pics:
        return None
    return _pic_url(pics[0])


def _pic_url(pic: object) -> str | None:
    if not isinstance(pic, dict):
        return None
    large = pic.get("large")
    if isinstance(large, dict):
        url = large.get("url")
        if url:
            return str(url).strip() or None
    url = pic.get("url")
    if url:
        return str(url).strip() or None
    return None
