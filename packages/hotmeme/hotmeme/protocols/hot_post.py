from __future__ import annotations

from typing import Protocol, runtime_checkable

from hotmeme.models import ImageItem, SourceConfigBase


@runtime_checkable
class HotPostSource(Protocol):
    """热帖源：按平台拉当前热门内容。"""

    provider_id: str
    config: SourceConfigBase
    is_implemented: bool

    def fetch_hot_posts(
        self,
        *,
        platform: str,
        allow_nsfw: bool | None = None,
    ) -> list[ImageItem]:
        ...
