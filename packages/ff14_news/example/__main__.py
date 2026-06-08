"""从包根目录运行：``example.bat`` 或 ``python -m example``。"""
from __future__ import annotations

import argparse
from pathlib import Path

from ff14_news import FF14News

from example.chat_print import make_console, print_feed_bundle


def _load_weibo_cookie(repo_root: Path) -> str | None:
    path = repo_root / "example" / "weibo_cookie.txt"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return None
    return "".join(lines)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    parser = argparse.ArgumentParser(
        description="并行抓取全部 FF14 新闻渠道，在终端以聊天样式展示。",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=5,
        help="每个渠道抓取列表前 N 条（默认 5）",
    )
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit 须 >= 1")

    weibo_cookie = _load_weibo_cookie(repo_root)
    weibo_storage = repo_root / "example" / ".weibo_browser_state.json"
    news = FF14News(
        cn_weibo_cookie=weibo_cookie,
        cn_weibo_cookie_storage_path=weibo_storage,
    )

    bundle = news.fetch_articles(limit=args.limit)
    channel_map = {channel_id: news.channel(channel_id) for channel_id in news.available_channels()}
    console = make_console()
    print_feed_bundle(
        bundle,
        channels=channel_map,
        channel_order=news.available_channels(),
        console=console,
    )

    if bundle.errors and not bundle.feeds:
        raise SystemExit(f"全部渠道抓取失败（{len(bundle.errors)}）")
    if bundle.errors:
        console.print(
            f"[chat.error]部分渠道失败：{len(bundle.errors)}[/]",
        )


if __name__ == "__main__":
    main()
