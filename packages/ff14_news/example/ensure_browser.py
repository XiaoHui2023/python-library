"""首次运行 example 前确保 Playwright Chromium 可用。"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from ff14_news.channels.cn_weibo.proxy_url import normalize_proxy_url


def _proxy_environ(proxy_url: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if proxy_url:
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        env["ALL_PROXY"] = proxy_url
    return env


def main() -> None:
    parser = argparse.ArgumentParser(description="确保 Playwright Chromium 已安装。")
    parser.add_argument(
        "--proxy",
        default="127.0.0.1:7897",
        help="下载浏览器内核时使用的 HTTP 代理（默认 127.0.0.1:7897）",
    )
    args = parser.parse_args()
    proxy = normalize_proxy_url(args.proxy)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return
    try:
        launch_kwargs: dict = {"headless": True}
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_kwargs)
            browser.close()
    except Exception:
        if proxy:
            print(f"正在通过代理 {proxy} 安装 Playwright Chromium（首次约 180MB）…")
        else:
            print("正在安装 Playwright Chromium（首次约 180MB）…")
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            env=_proxy_environ(proxy),
        )


if __name__ == "__main__":
    main()
