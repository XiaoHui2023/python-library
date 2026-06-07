from __future__ import annotations

from hotmeme.models import ImageItem

DEFAULT_COMMUNITY_BLOCKLIST = frozenset(
    {
        "nsfw",
        "gonewild",
        "realgirls",
        "porn",
        "politics",
        "worldpolitics",
        "watchpeopledie",
        "gore",
        "hate",
    },
)

DEFAULT_TITLE_KEYWORDS = frozenset(
    {
        "nsfw",
        "porn",
        "xxx",
    },
)


def filter_nsfw_items(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
    community_blocklist: frozenset[str] = DEFAULT_COMMUNITY_BLOCKLIST,
    title_keywords: frozenset[str] = DEFAULT_TITLE_KEYWORDS,
) -> list[ImageItem]:
    """按 NSFW 标记、社区黑名单与标题关键词过滤。"""
    if allow_nsfw:
        return list(items)
    kept: list[ImageItem] = []
    for item in items:
        if item.nsfw:
            continue
        community = (item.community or "").lower().lstrip("r/")
        if community in community_blocklist:
            continue
        title_lower = item.title.lower()
        if any(keyword in title_lower for keyword in title_keywords):
            continue
        kept.append(item)
    return kept
