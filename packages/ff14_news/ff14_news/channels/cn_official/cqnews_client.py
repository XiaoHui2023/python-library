import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from ff14_news.channels.cn_official.constants import (
    CHANNEL_ID,
    CQNEWS_API_BASE,
    GAME_CODE,
    OFFICIAL_NEWS_DETAIL_URL_TEMPLATE,
)
from ff14_news.models import NewsListItem

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; python-library-ff14-news/0.1)",
    "Accept": "application/json",
}


class CqNewsClient:
    """盛趣 cqnews 新闻 JSON 接口（国服官网 SPA 同源）。"""

    def __init__(self, timeout_seconds: float = 60.0) -> None:
        self._timeout = timeout_seconds

    def fetch_list_page(
        self,
        category_code: int,
        page_index: int,
        page_size: int,
    ) -> tuple[list[NewsListItem], int]:
        """拉取一页列表。

        Returns:
            列表项与 TotalCount。
        """
        query = urllib.parse.urlencode(
            {
                "gameCode": GAME_CODE,
                "CategoryCode": str(category_code),
                "pageIndex": str(page_index),
                "pageSize": str(page_size),
            }
        )
        url = f"{CQNEWS_API_BASE}/newsList?{query}"
        payload = self._get_json(url)
        rows = payload.get("Data") or []
        total = int(payload.get("TotalCount") or 0)
        items = [self._parse_list_row(row) for row in rows]
        return items, total

    def fetch_detail_raw(self, article_id: str) -> dict[str, Any]:
        """拉取详情 JSON 的 Data 字段。"""
        query = urllib.parse.urlencode(
            {"gameCode": GAME_CODE, "id": str(article_id).strip()}
        )
        url = f"{CQNEWS_API_BASE}/newsDetail?{query}"
        payload = self._get_json(url)
        data = payload.get("Data")
        if not isinstance(data, dict):
            msg = payload.get("Message") or "empty detail"
            raise ValueError(f"news detail {article_id} failed: {msg}")
        return data

    def _get_json(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(url, headers=_DEFAULT_HEADERS)
        try:
            raw = urllib.request.urlopen(req, timeout=self._timeout).read()
        except urllib.error.HTTPError as exc:
            raise ValueError(f"HTTP {exc.code} for {url}") from exc
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected JSON root from {url}")
        code = payload.get("Code")
        if code not in (0, "0", None):
            raise ValueError(
                f"API error Code={code} Message={payload.get('Message')}"
            )
        return payload

    def _parse_list_row(self, row: dict[str, Any]) -> NewsListItem:
        article_id = str(int(row["Id"]))
        return NewsListItem(
            channel_id=CHANNEL_ID,
            id=article_id,
            title=str(row.get("Title") or ""),
            publish_date=parse_publish_date(str(row.get("PublishDate") or "")),
            summary=str(row.get("Summary") or ""),
            cover_image_url=_optional_str(row.get("HomeImagePath")),
            source_page_url=OFFICIAL_NEWS_DETAIL_URL_TEMPLATE.format(
                article_id=article_id
            ),
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_publish_date(text: str) -> datetime:
    text = text.strip()
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported PublishDate: {text!r}")
