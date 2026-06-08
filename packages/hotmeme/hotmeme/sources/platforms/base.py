from __future__ import annotations

from abc import ABC, abstractmethod

from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.tikhub_client import TikHubClient


class PlatformWorkflow(ABC):
    """单平台热帖拉取工作流。"""

    platform: str

    @abstractmethod
    def fetch(self, client: TikHubClient) -> PlatformFetchResult:
        """按平台策略拉取热帖。"""
