from __future__ import annotations

import random
import time
from pathlib import Path

_MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-G9980) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/112.0.5615.135 Mobile Safari/537.36"
)
_MOBILE_HOME = "https://m.weibo.cn/"


def fetch_mobile_cookies(
    *,
    proxy_url: str | None = None,
    headless: bool = True,
    storage_state_path: Path | None = None,
    timeout_seconds: float = 60.0,
) -> dict[str, str]:
    """用 Playwright 打开 m.weibo.cn 并返回 Cookie 字典。

    Args:
        proxy_url: HTTP 代理，如 ``http://127.0.0.1:7897``
        headless: 是否无头运行 Chromium
        storage_state_path: 可复用的 Playwright storage state 路径
        timeout_seconds: 页面加载超时秒数
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "Playwright 未安装。请执行：pip install crawl4weibo && "
            "python -m example.ensure_browser --proxy 127.0.0.1:7897"
        ) from exc

    storage = None
    if storage_state_path is not None and storage_state_path.is_file():
        storage = str(storage_state_path.expanduser())

    launch_kwargs: dict = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ],
    }
    if proxy_url:
        launch_kwargs["proxy"] = {"server": proxy_url}

    cookies_dict: dict[str, str] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            user_agent=_MOBILE_UA,
            viewport={"width": 393, "height": 851},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            device_scale_factor=2.75,
            is_mobile=True,
            has_touch=True,
            storage_state=storage,
        )
        context.set_extra_http_headers(
            {
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/webp,*/*;q=0.8"
                ),
            },
        )
        page = context.new_page()
        try:
            page.goto(
                _MOBILE_HOME,
                timeout=int(timeout_seconds * 1000),
                wait_until="networkidle",
            )
            time.sleep(random.uniform(2, 4))
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(random.uniform(0.5, 1))
            for cookie in context.cookies():
                cookies_dict[cookie["name"]] = cookie["value"]
            if storage_state_path is not None:
                storage_state_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(storage_state_path))
        finally:
            context.close()
            browser.close()
    return cookies_dict
