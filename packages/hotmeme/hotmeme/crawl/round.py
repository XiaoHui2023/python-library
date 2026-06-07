from __future__ import annotations

from dataclasses import dataclass, field

from hotmeme.cn_models import TopicItem
from hotmeme.models import ImageItem


@dataclass
class FetchedRound:
    """单次爬取各源原始合并结果（未做「相对上次」增量）。"""

    items: list[ImageItem] = field(default_factory=list)
    topics: list[TopicItem] = field(default_factory=list)
    providers_ok: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
