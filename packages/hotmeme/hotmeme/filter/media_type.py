from __future__ import annotations

from hotmeme.models import ImageItem, MediaType


def filter_media_types(
    items: list[ImageItem],
    *,
    allowed: list[MediaType] | None = None,
) -> list[ImageItem]:
    """按允许的 ``MediaType`` 丢弃条目。"""
    if not allowed:
        return items
    allowed_set = set(allowed)
    return [item for item in items if item.media_type in allowed_set]
