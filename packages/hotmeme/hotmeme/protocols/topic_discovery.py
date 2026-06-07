from __future__ import annotations

from typing import Protocol, runtime_checkable

from hotmeme.cn_models import TopicItem
from hotmeme.models import SourceConfigBase


@runtime_checkable
class TopicDiscoverySource(Protocol):
    """中国热点发现源：各接入项目独立拉取热榜。"""

    provider_id: str
    config: SourceConfigBase
    is_implemented: bool

    def discover(
        self,
        *,
        platforms: list[str] | None = None,
        limit: int | None = None,
    ) -> list[TopicItem]:
        ...
