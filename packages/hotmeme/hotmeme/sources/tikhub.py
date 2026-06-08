from __future__ import annotations

from hotmeme.common.errors import TikHubApiError
from hotmeme.models import ImageItem, TikHubApiCall, TikHubConfig, XiaohongshuPolicy
from hotmeme.sources.base import BaseHotPostSource
from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.platforms import fetch_platform_hot_posts
from hotmeme.sources.tikhub_client import TikHubClient


class TikHubSource(BaseHotPostSource):
    """TikHub：按平台工作流拉热门帖。"""

    provider_id = "tikhub"
    is_implemented = True

    def __init__(self, config: TikHubConfig) -> None:
        super().__init__(config)
        self._config = config
        self._client_obj: TikHubClient | None = None

    def _client(self) -> TikHubClient:
        if self._client_obj is not None:
            return self._client_obj
        api_key = self._config.api_key
        if not api_key:
            raise TikHubApiError("TikHub api_key 未配置")
        self._client_obj = TikHubClient(
            api_key=api_key,
            timeout=self._config.timeout,
        )
        return self._client_obj

    @property
    def api_calls(self) -> list[TikHubApiCall]:
        if self._client_obj is None:
            return []
        return list(self._client_obj.request_log)

    def fetch_hot_posts(
        self,
        *,
        platform: str,
        allow_nsfw: bool | None = None,
        xiaohongshu: XiaohongshuPolicy | None = None,
    ) -> list[ImageItem]:
        return self.fetch_platform_result(
            platform=platform,
            allow_nsfw=allow_nsfw,
            xiaohongshu=xiaohongshu,
        ).items

    def fetch_platform_result(
        self,
        *,
        platform: str,
        allow_nsfw: bool | None = None,
        xiaohongshu: XiaohongshuPolicy | None = None,
    ) -> PlatformFetchResult:
        client = self._client()
        result = fetch_platform_hot_posts(
            client,
            platform=platform,
            xiaohongshu=xiaohongshu,
        )
        allow = allow_nsfw if allow_nsfw is not None else self._config.allow_nsfw
        if not allow:
            result.items = [item for item in result.items if not item.nsfw]
        return result
