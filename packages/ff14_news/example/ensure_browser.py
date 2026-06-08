"""首次运行 example 前确保 Playwright Chromium 可用。"""
from __future__ import annotations

import subprocess
import sys


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception:
        print("正在安装 Playwright Chromium（首次约 180MB）…")
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install", "chromium"],
        )


if __name__ == "__main__":
    main()
