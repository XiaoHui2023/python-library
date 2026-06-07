from __future__ import annotations

from hotmeme.cn_models import TikHubConfig
from hotmeme.sources.cn.base import BaseContentSource


class TikHubSource(BaseContentSource):
    """TikHub 平台搜图（第一版目标源）。"""

    provider_id = "tikhub"
    is_implemented = False

    def __init__(self, config: TikHubConfig) -> None:
        super().__init__(config)
