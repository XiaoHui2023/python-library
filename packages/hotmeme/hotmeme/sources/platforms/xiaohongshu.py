from __future__ import annotations

from hotmeme.models import ImageItem, XiaohongshuPolicy
from hotmeme.sources.parsers.xiaohongshu import parse_xhs_search_notes, parse_xhs_tag_name
from hotmeme.sources.platforms.base import PlatformWorkflow
from hotmeme.sources.tikhub_client import TikHubClient

_SEARCH_PATH = "/api/v1/xiaohongshu/app_v2/search_notes"


class XiaohongshuWorkflow(PlatformWorkflow):
    """小红书：按话题 tag 搜索笔记。"""

    platform = "xiaohongshu"

    def __init__(self, policy: XiaohongshuPolicy | None = None) -> None:
        self._policy = policy or XiaohongshuPolicy()

    def fetch(self, client: TikHubClient) -> list[ImageItem]:
        keywords = self._policy.search_keywords()
        if not keywords:
            return []

        items: list[ImageItem] = []
        seen: set[str] = set()
        for keyword in keywords:
            tag_name = parse_xhs_tag_name(keyword)
            data = client.get(
                _SEARCH_PATH,
                {
                    "keyword": keyword,
                    "page": self._policy.page,
                    "sort_type": self._policy.sort_type,
                    "time_filter": self._policy.time_filter,
                    "note_type": self._policy.note_type,
                },
            )
            for item in parse_xhs_search_notes(data):
                if item.id in seen:
                    continue
                seen.add(item.id)
                tagged = item
                if tag_name:
                    tagged = item.model_copy(update={"search_tag": tag_name})
                items.append(tagged)
        return items
