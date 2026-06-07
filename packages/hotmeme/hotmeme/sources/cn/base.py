from __future__ import annotations

from hotmeme.cn_models import TopicItem
from hotmeme.common.errors import CnSourceNotImplementedError
from hotmeme.models import ImageItem, SourceConfigBase


class BaseDiscoverySource:
    """热点发现源基类。"""

    provider_id: str
    is_implemented: bool = False

    def __init__(self, config: SourceConfigBase) -> None:
        self.config = config

    def discover(
        self,
        *,
        platforms: list[str] | None = None,
        limit: int | None = None,
    ) -> list[TopicItem]:
        raise CnSourceNotImplementedError(
            f"{self.provider_id} 热点发现尚未接入",
        )


class BaseContentSource:
    """内容图片源基类。"""

    provider_id: str
    is_implemented: bool = False

    def __init__(self, config: SourceConfigBase) -> None:
        self.config = config

    def search_images(
        self,
        query: str,
        *,
        platform: str,
        limit: int | None = None,
        topic: str | None = None,
        allow_nsfw: bool | None = None,
    ) -> list[ImageItem]:
        raise CnSourceNotImplementedError(
            f"{self.provider_id} 内容搜索尚未接入",
        )
