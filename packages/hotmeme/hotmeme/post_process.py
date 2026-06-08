from __future__ import annotations

from hotmeme.models import ImageItem, MediaType
from hotmeme.pipeline.diagnostics import post_process_traced

LOCAL_FILTER_CHAIN = "displayable,media_types,nsfw,risk,min_score,dedup,rank"


def post_process(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
    media_types: list[MediaType] | None = None,
    platform_min_scores: dict[str, float] | None = None,
) -> list[ImageItem]:
    """热帖聚合结果的后处理。"""
    processed, _stages = post_process_traced(
        items,
        allow_nsfw=allow_nsfw,
        media_types=media_types,
        platform_min_scores=platform_min_scores,
    )
    return processed
