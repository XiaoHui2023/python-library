from __future__ import annotations

from dataclasses import dataclass, field

from hotmeme.models import FetchDiagnostics, ImageItem, TikHubApiCall


@dataclass
class FetchedRound:
    """单次爬取原始合并结果（未做相对上次增量）。"""

    items: list[ImageItem] = field(default_factory=list)
    providers_ok: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
    fetch_errors: list[str] = field(default_factory=list)
    api_calls: list[TikHubApiCall] = field(default_factory=list)
    diagnostics: FetchDiagnostics | None = None
