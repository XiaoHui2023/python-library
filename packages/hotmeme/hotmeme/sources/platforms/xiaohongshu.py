from __future__ import annotations

from hotmeme.models import XiaohongshuPolicy
from hotmeme.pipeline.diagnostics import XhsKeywordFetchStat
from hotmeme.sources.parsers.xiaohongshu import (
    parse_xhs_search_notes_traced,
    parse_xhs_tag_name,
)
from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.platforms.base import PlatformWorkflow
from hotmeme.sources.tikhub_client import TikHubClient

_SEARCH_PATH = "/api/v1/xiaohongshu/app_v2/search_notes"


class XiaohongshuWorkflow(PlatformWorkflow):
    """小红书：按话题 tag 搜索笔记。"""

    platform = "xiaohongshu"

    def __init__(self, policy: XiaohongshuPolicy | None = None) -> None:
        self._policy = policy or XiaohongshuPolicy()

    def fetch(self, client: TikHubClient) -> PlatformFetchResult:
        keywords = self._policy.search_keywords()
        if not keywords:
            return PlatformFetchResult()

        items = []
        seen: set[str] = set()
        keyword_stats: list[XhsKeywordFetchStat] = []
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
            batch, parse_stats = parse_xhs_search_notes_traced(data)
            tag_dedup_skipped = 0
            merged = 0
            for item in batch:
                if item.id in seen:
                    tag_dedup_skipped += 1
                    continue
                seen.add(item.id)
                tagged = item
                if tag_name:
                    tagged = item.model_copy(update={"search_tag": tag_name})
                items.append(tagged)
                merged += 1
            keyword_stats.append(
                XhsKeywordFetchStat(
                    keyword=keyword,
                    search_tag=tag_name,
                    api_list_items=parse_stats.api_list_items,
                    note_candidates=parse_stats.note_candidates,
                    parsed_with_media=parse_stats.parsed_with_media,
                    no_media=parse_stats.no_media,
                    tag_dedup_skipped=tag_dedup_skipped,
                    merged_items=merged,
                ),
            )
        return PlatformFetchResult(items=items, xhs_keyword_stats=keyword_stats)
