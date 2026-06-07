"""从包根目录运行：``example.bat`` 或 ``python -m example``。"""
from __future__ import annotations

import argparse
from pathlib import Path

from ff14_news import FF14News
from ff14_news.channels.cn_weibo.exceptions import WeiboAccessError

from example.export_feed import export_feed_to_directory


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
    default_out = repo_root / "example" / "output"

    parser = argparse.ArgumentParser(
        description="按渠道抓取 FF14 新闻并导出 JSON/Markdown，图片保存到本地。",
    )
    parser.add_argument(
        "-c",
        "--channel",
        default="all",
        choices=["cn_official", "cn_weibo", "jp_official", "all"],
        help="渠道：all=全部（默认）；或指定 cn_official / cn_weibo / jp_official",
    )
    parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=2,
        help="每个渠道抓取列表前 N 条（默认 2）",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"输出根目录（默认 {default_out}，其下按渠道分子目录）",
    )
    parser.add_argument(
        "--proxy",
        default="127.0.0.1:7897",
        help="微博渠道 HTTP 代理（默认 127.0.0.1:7897；传空串表示不走代理）",
    )
    args = parser.parse_args()
    if args.limit < 1:
        raise SystemExit("--limit 须 >= 1")

    weibo_cookie = _load_weibo_cookie(repo_root)
    weibo_storage = repo_root / "example" / ".weibo_browser_state.json"
    weibo_proxy = args.proxy.strip() or None
    news = FF14News(
        cn_weibo_cookie=weibo_cookie,
        cn_weibo_cookie_storage_path=weibo_storage,
        cn_weibo_proxy_url=weibo_proxy,
    )
    if args.channel == "all":
        channel_ids = news.available_channels()
    else:
        channel_ids = [args.channel]

    args.output.mkdir(parents=True, exist_ok=True)
    failed = 0
    for channel_id in channel_ids:
        ch = news.channel(channel_id)
        try:
            feed = ch.fetch_articles(limit=args.limit)
        except WeiboAccessError as exc:
            failed += 1
            print(f"[{channel_id}] 跳过：{exc}")
            continue
        except ValueError as exc:
            failed += 1
            print(f"[{channel_id}] 跳过：{exc}")
            continue
        channel_dir = export_feed_to_directory(feed, args.output / channel_id)
        print(f"[{channel_id}] 已写入：{channel_dir}")
        print("  feed.json")
        for article in feed.articles:
            sub = channel_dir / str(article.id)
            print(f"  {sub.name}/article.json")
            print(f"  {sub.name}/article.md")
            print(f"  {sub.name}/images/")
    if failed:
        raise SystemExit(f"{failed} 个渠道抓取失败")


if __name__ == "__main__":
    main()
