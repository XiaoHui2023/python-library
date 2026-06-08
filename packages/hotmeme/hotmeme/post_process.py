from __future__ import annotations

from hotmeme.models import ImageItem
from hotmeme.pipeline.diagnostics import post_process_traced

LOCAL_FILTER_CHAIN = "displayable,nsfw,risk,low_interest,dedup,rank"


def post_process(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
) -> list[ImageItem]:
    """热帖聚合结果的后处理。"""
    processed, _stages = post_process_traced(items, allow_nsfw=allow_nsfw)
    return processed
