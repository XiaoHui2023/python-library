from __future__ import annotations

from urllib.parse import urlparse

from hotmeme.models import MediaType


def guess_media_type(url: str) -> MediaType:
    """由 URL 路径猜测媒体类型。"""
    path = urlparse(url).path.lower()
    if path.endswith(".gif"):
        return MediaType.GIF
    if path.endswith((".mp4", ".webm", ".mov")):
        return MediaType.VIDEO
    return MediaType.IMAGE
