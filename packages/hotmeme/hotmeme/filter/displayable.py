from __future__ import annotations

from hotmeme.models import ImageItem, MediaType


def has_displayable_media(item: ImageItem) -> bool:
    """帖子是否含可展示图或视频。"""
    if item.media_type == MediaType.VIDEO:
        return bool(item.video_url)
    if item.media_type == MediaType.VIDEO_COVER:
        return bool(item.image_url)
    return bool(item.image_url)


def filter_displayable_media(items: list[ImageItem]) -> list[ImageItem]:
    """丢弃无图且无视频的条目。"""
    return [item for item in items if has_displayable_media(item)]
