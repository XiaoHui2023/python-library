from __future__ import annotations

from hotmeme.filter import dedup_items, filter_cn_risk_items, filter_nsfw_items
from hotmeme.merge.rank import sort_items
from hotmeme.models import ImageItem


def post_process_cn(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
    total_limit: int,
) -> list[ImageItem]:
    """中国源聚合结果的后处理。"""
    filtered = filter_nsfw_items(items, allow_nsfw=allow_nsfw)
    filtered = filter_cn_risk_items(filtered)
    filtered = dedup_items(filtered)
    filtered = sort_items(filtered)
    return filtered[:total_limit]
