from __future__ import annotations

from hotmeme.common.errors import SourceNotImplementedError
from hotmeme.models import ImageItem, SourceConfigBase


class BaseHotPostSource:
    """热帖源基类。"""

    provider_id: str
    is_implemented: bool = False

    def __init__(self, config: SourceConfigBase) -> None:
        self.config = config

    def fetch_hot_posts(
        self,
        *,
        platform: str,
        allow_nsfw: bool | None = None,
    ) -> list[ImageItem]:
        raise SourceNotImplementedError(
            f"{self.provider_id} 热帖拉取尚未接入",
        )
