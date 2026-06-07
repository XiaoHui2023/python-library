from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.models import ImageItem, MediaType

HIGH_QUALITY_COMMUNITIES = frozenset(
    {
        "memes",
        "dankmemes",
        "programmerhumor",
        "wholesomememes",
    },
)


def rank_score(item: ImageItem, *, now: datetime | None = None) -> float:
    """把来源分数、时间、社区质量折成可比较的排序分。"""
    now = now or datetime.now(UTC)
    score = float(item.score or 0.0)
    if item.created_at is not None:
        created = item.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_hours = max((now - created).total_seconds() / 3600.0, 0.0)
        score += max(0.0, 48.0 - age_hours) * 2.0
    else:
        score += 10.0
    if item.media_type == MediaType.GIF:
        score += 3.0
    community = (item.community or "").lower().lstrip("r/")
    if community in HIGH_QUALITY_COMMUNITIES:
        score += 8.0
    if item.width and item.height:
        area = item.width * item.height
        if 200_000 <= area <= 2_000_000:
            score += 4.0
    return score


def sort_items(items: list[ImageItem]) -> list[ImageItem]:
    """按统一排序分降序排列。"""
    return sorted(items, key=lambda item: rank_score(item), reverse=True)
