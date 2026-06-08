from __future__ import annotations

from hotmeme.models import ImageItem
from hotmeme.sources.parsers.douyin import (
    extract_douyin_hot_keywords,
    parse_douyin_video_search,
)
from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.platforms.base import PlatformWorkflow
from hotmeme.sources.tikhub_client import TikHubClient


class DouyinWorkflow(PlatformWorkflow):
    """抖音：热榜关键词 → 视频搜索。"""

    platform = "douyin"
    _SEARCH_TIMEOUT = 45.0

    def fetch(self, client: TikHubClient) -> PlatformFetchResult:
        hot_data = client.get("/api/v1/douyin/web/fetch_hot_search_result")
        keywords = extract_douyin_hot_keywords(hot_data, limit=1)
        if not keywords:
            return PlatformFetchResult()

        items: list[ImageItem] = []
        seen: set[str] = set()
        for keyword in keywords:
            data = client.post(
                "/api/v1/douyin/search/fetch_general_search_v2",
                {
                    "keyword": keyword,
                    "cursor": 0,
                    "sort_type": "1",
                    "publish_time": "1",
                    "filter_duration": "0",
                    "content_type": "0",
                    "search_id": "",
                },
                timeout=self._SEARCH_TIMEOUT,
            )
            for item in parse_douyin_video_search(data):
                if item.id in seen:
                    continue
                seen.add(item.id)
                items.append(item)
        return PlatformFetchResult(items=items)
