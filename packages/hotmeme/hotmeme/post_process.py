from __future__ import annotations

from hotmeme.filter import (
    dedup_items,
    filter_displayable_media,
    filter_low_interest_items,
    filter_nsfw_items,
    filter_risk_items,
)
from hotmeme.merge.rank import sort_items
from hotmeme.models import ImageItem

LOCAL_FILTER_CHAIN = "displayable,nsfw,risk,low_interest,dedup,rank"


def post_process(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
) -> list[ImageItem]:
    """热帖聚合结果的后处理。"""
    filtered = filter_displayable_media(items)
    filtered = filter_nsfw_items(filtered, allow_nsfw=allow_nsfw)
    filtered = filter_risk_items(filtered)
    filtered = filter_low_interest_items(filtered)
    filtered = dedup_items(filtered)
    filtered = sort_items(filtered)
    return filtered
