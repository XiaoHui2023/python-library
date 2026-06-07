from __future__ import annotations

from pathlib import Path

from crawl4weibo import WeiboClient
from crawl4weibo.exceptions.base import CrawlError, NetworkError, RateLimitError
from crawl4weibo.models.post import Post

from ff14_news.channels.cn_weibo.browser_cookies import fetch_mobile_cookies
from ff14_news.channels.cn_weibo.exceptions import WeiboAccessError
from ff14_news.channels.cn_weibo.proxy_url import normalize_proxy_url

_PLAYWRIGHT_INSTALL_HINT = (
    "请先安装 Playwright Chromium：\n"
    "  python -m example.ensure_browser --proxy 127.0.0.1:7897"
)


class WeiboCrawlBackend:
    """基于 crawl4weibo 的微博 HTTP 后端（Playwright 取 Cookie + 移动端 API）。"""

    def __init__(
        self,
        *,
        cookie: str | None = None,
        cookie_storage_path: Path | None = None,
        browser_headless: bool = True,
        proxy_url: str | None = None,
    ) -> None:
        """创建后端。

        Args:
            cookie: 浏览器 Cookie 整串；提供后不再自动开浏览器
            cookie_storage_path: Playwright 会话缓存路径，可复用 Cookie
            browser_headless: 自动取 Cookie 时是否无头运行 Chromium
            proxy_url: HTTP 代理，如 ``127.0.0.1:7897`` 或 ``http://127.0.0.1:7897``
        """
        self._proxy = normalize_proxy_url(proxy_url)
        if cookie:
            cookie_value: str | dict[str, str] = cookie
        else:
            try:
                cookie_value = fetch_mobile_cookies(
                    proxy_url=self._proxy,
                    headless=browser_headless,
                    storage_state_path=cookie_storage_path,
                )
            except Exception as exc:
                raise _access_error(exc) from exc
            if not cookie_value:
                raise WeiboAccessError(
                    "Playwright 未获取到微博 Cookie，请检查代理或手动配置 Cookie。"
                )
        try:
            self._client = WeiboClient(
                cookies=cookie_value,
                auto_fetch_cookies=False,
                use_browser_cookies=False,
                log_level="WARNING",
            )
        except Exception as exc:
            raise _access_error(exc) from exc
        if self._proxy:
            self._client.add_proxy(self._proxy)

    def resolve_screen_name(self, screen_name: str) -> str:
        """按 screen_name 解析 numeric uid。"""
        name = screen_name.strip()
        if not name:
            raise ValueError("screen_name must not be empty")
        try:
            users = self._client.search_users(name, count=20)
        except (CrawlError, NetworkError, RateLimitError) as exc:
            raise _access_error(exc) from exc
        lowered = name.lower()
        for user in users:
            if user.screen_name.lower() == lowered:
                return str(user.id)
        raise ValueError(f"cannot resolve uid for screen_name={name!r}")

    def fetch_timeline_posts(self, uid: str, *, page: int) -> list[Post]:
        """拉取用户时间线一页。"""
        if page < 1:
            raise ValueError("page must be >= 1")
        try:
            return self._client.get_user_posts(
                uid,
                page=page,
                expand=False,
            )
        except (CrawlError, NetworkError, RateLimitError) as exc:
            raise _access_error(exc) from exc

    def fetch_post(self, article_id: str) -> Post:
        """拉取单条微博（列表级字段，不展开长文）。"""
        article_id = str(article_id).strip()
        if not article_id:
            raise ValueError("article_id must not be empty")
        try:
            return self._client.get_post_by_bid(article_id, expand=False)
        except (CrawlError, NetworkError, RateLimitError) as exc:
            raise _access_error(exc) from exc

    def fetch_post_detail(self, article_id: str) -> Post:
        """拉取单条微博详情（展开长文）。"""
        article_id = str(article_id).strip()
        if not article_id:
            raise ValueError("article_id must not be empty")
        try:
            return self._client.get_post_by_bid(article_id, expand=True)
        except (CrawlError, NetworkError, RateLimitError) as exc:
            raise _access_error(exc) from exc


def _access_error(exc: Exception) -> WeiboAccessError:
    message = str(exc).strip()
    lowered = message.lower()
    if "playwright" in lowered or "executable" in lowered or "chromium" in lowered:
        return WeiboAccessError(
            f"微博需要 Playwright Chromium。{_PLAYWRIGHT_INSTALL_HINT}"
        )
    if "432" in message:
        return WeiboAccessError(
            "微博返回 HTTP 432。"
            f"请确认代理可用（如 127.0.0.1:7897），或配置 example/weibo_cookie.txt。"
        )
    if isinstance(exc, RateLimitError):
        return WeiboAccessError(f"微博限流：{message}")
    return WeiboAccessError(message or "微博请求失败")
