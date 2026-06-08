from __future__ import annotations

from hotmeme.models import ImageItem


def filter_min_score_items(
    items: list[ImageItem],
    *,
    platform_min_scores: dict[str, float],
) -> list[ImageItem]:
    """按平台最低互动分丢弃条目；阈值为「须严格大于」该值。"""
    if not platform_min_scores:
        return list(items)
    kept: list[ImageItem] = []
    for item in items:
        platform = (item.community or "").strip().lower()
        threshold = platform_min_scores.get(platform)
        if threshold is None:
            kept.append(item)
            continue
        score = item.score
        if score is not None and score > threshold:
            kept.append(item)
    return kept
