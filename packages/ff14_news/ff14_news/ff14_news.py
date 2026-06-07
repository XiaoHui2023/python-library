from pathlib import Path

from ff14_news.channel_protocol import NewsChannel
from ff14_news.channels.cn_official import CnOfficialChannel
from ff14_news.channels.cn_weibo import CnWeiboChannel
from ff14_news.channels.jp_official import JpOfficialChannel


class FF14News:
    """FF14 新闻聚合门面：各渠道独立实现，通过属性访问。"""

    def __init__(
        self,
        *,
        cn_official_timeout_seconds: float = 60.0,
        cn_weibo_timeout_seconds: float = 60.0,
        cn_weibo_cookie: str | None = None,
        cn_weibo_cookie_storage_path: Path | str | None = None,
        cn_weibo_browser_headless: bool = True,
        cn_weibo_proxy_url: str | None = None,
        jp_official_timeout_seconds: float = 120.0,
    ) -> None:
        """聚合各渠道实例。

        Args:
            cn_official_timeout_seconds: 国服官网 HTTP 超时
            cn_weibo_timeout_seconds: 微博渠道 HTTP 超时
            cn_weibo_cookie: 微博 m.weibo.cn Cookie 整串；未提供时用 Playwright 自动获取
            cn_weibo_cookie_storage_path: Playwright 会话缓存路径
            cn_weibo_browser_headless: 微博自动取 Cookie 时是否无头浏览器
            cn_weibo_proxy_url: 微博 HTTP 代理，如 ``127.0.0.1:7897``
            jp_official_timeout_seconds: 日文 Lodestone HTTP 超时
        """
        self.cn_official = CnOfficialChannel(
            timeout_seconds=cn_official_timeout_seconds,
        )
        weibo_storage = (
            Path(cn_weibo_cookie_storage_path).expanduser()
            if cn_weibo_cookie_storage_path is not None
            else None
        )
        self.cn_weibo = CnWeiboChannel(
            timeout_seconds=cn_weibo_timeout_seconds,
            cookie=cn_weibo_cookie,
            cookie_storage_path=weibo_storage,
            browser_headless=cn_weibo_browser_headless,
            proxy_url=cn_weibo_proxy_url,
        )
        self.jp_official = JpOfficialChannel(
            timeout_seconds=jp_official_timeout_seconds,
        )

    def available_channels(self) -> list[str]:
        return ["cn_official", "cn_weibo", "jp_official"]

    def channel(self, channel_id: str) -> NewsChannel:
        if channel_id == "cn_official":
            return self.cn_official
        if channel_id == "cn_weibo":
            return self.cn_weibo
        if channel_id == "jp_official":
            return self.jp_official
        known = ", ".join(self.available_channels())
        raise KeyError(f"unknown channel {channel_id!r}; known: {known}")
