from __future__ import annotations

from typing import Protocol, runtime_checkable

from hotmeme.models import ImageItem, SourceConfigBase


@runtime_checkable
class ContentImageSource(Protocol):
    """中国内容图片源：按关键词在指定平台搜图。"""

    provider_id: str
    config: SourceConfigBase
    is_implemented: bool

    def search_images(
        self,
        query: str,
        *,
        platform: str,
        limit: int | None = None,
        topic: str | None = None,
        allow_nsfw: bool | None = None,
    ) -> list[ImageItem]:
        ...
