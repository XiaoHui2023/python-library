from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from ff14_news.channel_protocol import NewsChannel
from ff14_news.channels.cn_official import CnOfficialChannel
from ff14_news.channels.cn_weibo import CnWeiboChannel
from ff14_news.channels.jp_official import JpOfficialChannel
from ff14_news.models import NewsChannelFetchError, NewsFeed, NewsFeedBundle

_ALL_CHANNEL_IDS = ("cn_official", "cn_weibo", "jp_official")


class FF14News:
    """FF14 新闻聚合门面：构造时开关渠道，并行抓取返回 NewsFeedBundle。"""

    def __init__(
        self,
        *,
        enable_cn_official: bool = True,
        enable_cn_weibo: bool = True,
        enable_jp_official: bool = True,
        cn_official_timeout_seconds: float = 60.0,
        cn_weibo_timeout_seconds: float = 60.0,
        cn_weibo_cookie: str | None = None,
        cn_weibo_cookie_storage_path: Path | str | None = None,
        cn_weibo_browser_headless: bool = True,
        jp_official_timeout_seconds: float = 120.0,
    ) -> None:
        """聚合各渠道实例；未启用的渠道不构造、不可访问。

        Args:
            enable_cn_official: 是否启用国服官网渠道
            enable_cn_weibo: 是否启用官方微博渠道
            enable_jp_official: 是否启用日文 Lodestone 渠道
            cn_official_timeout_seconds: 国服官网 HTTP 超时
            cn_weibo_timeout_seconds: 微博渠道 HTTP 超时
            cn_weibo_cookie: 微博 m.weibo.cn Cookie 整串；未提供时用 Playwright 自动获取
            cn_weibo_cookie_storage_path: Playwright 会话缓存路径
            cn_weibo_browser_headless: 微博自动取 Cookie 时是否无头浏览器
            jp_official_timeout_seconds: 日文 Lodestone HTTP 超时
        """
        self._channels: dict[str, NewsChannel] = {}
        if enable_cn_official:
            self._channels["cn_official"] = CnOfficialChannel(
                timeout_seconds=cn_official_timeout_seconds,
            )
        if enable_cn_weibo:
            weibo_storage = (
                Path(cn_weibo_cookie_storage_path).expanduser()
                if cn_weibo_cookie_storage_path is not None
                else None
            )
            self._channels["cn_weibo"] = CnWeiboChannel(
                timeout_seconds=cn_weibo_timeout_seconds,
                cookie=cn_weibo_cookie,
                cookie_storage_path=weibo_storage,
                browser_headless=cn_weibo_browser_headless,
            )
        if enable_jp_official:
            self._channels["jp_official"] = JpOfficialChannel(
                timeout_seconds=jp_official_timeout_seconds,
            )

    @property
    def cn_official(self) -> CnOfficialChannel:
        return self._require_channel("cn_official")

    @property
    def cn_weibo(self) -> CnWeiboChannel:
        return self._require_channel("cn_weibo")

    @property
    def jp_official(self) -> JpOfficialChannel:
        return self._require_channel("jp_official")

    def available_channels(self) -> list[str]:
        return [channel_id for channel_id in _ALL_CHANNEL_IDS if channel_id in self._channels]

    def channel(self, channel_id: str) -> NewsChannel:
        return self._require_channel(channel_id)

    def fetch_articles(
        self,
        *,
        limit: int = 10,
        page_index: int = 0,
    ) -> NewsFeedBundle:
        """并行抓取所有已启用渠道的列表级新闻。

        Args:
            limit: 每个渠道抓取列表前 N 条
            page_index: 列表分页索引（各渠道语义一致）

        Returns:
            成功 feed 与失败记录合在一起的 NewsFeedBundle

        Raises:
            ValueError: 未启用任何渠道
        """
        if not self._channels:
            raise ValueError("no channels enabled")

        feeds: dict[str, NewsFeed] = {}
        errors: list[NewsChannelFetchError] = []
        worker_count = len(self._channels)

        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = {
                pool.submit(
                    self._fetch_channel_articles,
                    channel_id,
                    channel,
                    limit,
                    page_index,
                ): channel_id
                for channel_id, channel in self._channels.items()
            }
            for future in as_completed(futures):
                channel_id, feed, error_message = future.result()
                if feed is not None:
                    feeds[channel_id] = feed
                else:
                    errors.append(
                        NewsChannelFetchError(
                            channel_id=channel_id,
                            message=error_message or "unknown error",
                        )
                    )

        return NewsFeedBundle(
            fetched_at=datetime.now(timezone.utc),
            feeds=feeds,
            errors=errors,
        )

    def _require_channel(self, channel_id: str) -> NewsChannel:
        channel = self._channels.get(channel_id)
        if channel is None:
            enabled = ", ".join(self.available_channels()) or "(none)"
            raise KeyError(
                f"channel {channel_id!r} is disabled; enabled: {enabled}",
            )
        return channel

    @staticmethod
    def _fetch_channel_articles(
        channel_id: str,
        channel: NewsChannel,
        limit: int,
        page_index: int,
    ) -> tuple[str, NewsFeed | None, str | None]:
        try:
            feed = channel.fetch_articles(limit=limit, page_index=page_index)
        except Exception as exc:
            return channel_id, None, _format_exception_chain(exc)
        return channel_id, feed, None


def _format_exception_chain(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(_format_exception(current))
        current = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__
        )
    return " | caused by: ".join(parts)


def _format_exception(exc: BaseException) -> str:
    exc_type = type(exc).__name__
    message = str(exc).strip()
    return f"{exc_type}: {message}" if message else exc_type
