from __future__ import annotations

from hotmeme.cn_models import HotpushConfig
from hotmeme.sources.cn.base import BaseDiscoverySource


class HotpushSource(BaseDiscoverySource):
    """hotpush 热点推送（运营版接入）。"""

    provider_id = "hotpush"
    is_implemented = False

    def __init__(self, config: HotpushConfig) -> None:
        super().__init__(config)
