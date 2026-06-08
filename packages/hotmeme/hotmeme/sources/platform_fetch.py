from __future__ import annotations

from dataclasses import dataclass, field

from hotmeme.models import ImageItem
from hotmeme.pipeline.diagnostics import XhsKeywordFetchStat


@dataclass
class PlatformFetchResult:
    """单平台工作流拉取结果。"""

    items: list[ImageItem] = field(default_factory=list)
    xhs_keyword_stats: list[XhsKeywordFetchStat] = field(default_factory=list)
