import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from hotmeme import HotMeme, supported_platforms
from hotmeme.pipeline.fetch_plan import (
    describe_expected_api_calls,
    local_filter_chain,
    min_expected_call_count,
)

EXAMPLE_DIR = Path(__file__).resolve().parent
CONFIG = EXAMPLE_DIR / "config.example.yaml"


def _load_api_key() -> str:
    load_dotenv(EXAMPLE_DIR / ".env")
    api_key = os.environ.get("TIKHUB_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "缺少 TIKHUB_API_KEY：请复制 example/.env.example 为 example/.env 并填写",
        )
    return api_key


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="hotmeme 示例：拉取并渲染热帖")
    parser.add_argument(
        "-p",
        "--platform",
        choices=supported_platforms(),
        help="只拉指定平台（覆盖配置文件 pipeline.platforms）",
    )
    parser.add_argument("--json", action="store_true", help="额外打印完整 JSON 输出")
    return parser.parse_args()


def _print_api_plan(client: HotMeme, platforms: list[str]) -> None:
    xhs = client.config.xiaohongshu
    print("=== TikHub 计划请求（按次计费）===")
    for line in describe_expected_api_calls(platforms, xiaohongshu=xhs):
        print(line)
    print(f"最少约 {min_expected_call_count(platforms, xiaohongshu=xhs)} 次 TikHub 请求")
    print()
    print("=== 筛选说明 ===")
    print("API/来源层：各平台请求参数见 api_filters；NSFW 由 allow_nsfw 控制")
    print(f"本地后处理：{local_filter_chain()}（不在 TikHub 参数里筛趣味/祝福类标题）")
    print()


def _print_api_actual(api_calls: list) -> None:
    print(f"=== 实际 TikHub 请求（共 {len(api_calls)} 次）===")
    for index, call in enumerate(api_calls, start=1):
        params = call.params
        params_text = ""
        if params:
            params_text = f" {params}"
        print(f"{index}. {call.method} {call.path}{params_text}")
    print()


def _print_packet(index: int, total: int, pkt) -> None:
    print(f"--- [{index}/{total}] {pkt.title[:80]} ---")
    print(f"platform: {pkt.platform}")
    if pkt.search_tag:
        print(f"search_tag: {pkt.search_tag}")
    print(f"provider: {pkt.provider}")
    print(f"source_id: {pkt.source_id}")
    print(f"media_type: {pkt.media_type}")
    print(f"media_kind: {pkt.media_kind.value}")
    print(f"score: {pkt.score}")
    print(f"rank_score: {pkt.rank_score:.2f}" if pkt.rank_score is not None else "rank_score: -")
    print(f"nsfw: {pkt.nsfw}")
    if pkt.risk_flags:
        print(f"risk_flags: {','.join(pkt.risk_flags)}")
    print(f"api_filters: {pkt.api_filters}")
    print(f"post_filters: {pkt.post_filters}")
    print(f"author: {pkt.author or '-'}")
    print(f"source_url: {pkt.source_url}")
    if pkt.image_url:
        print(f"image_url: {pkt.image_url}")
    if pkt.video_url:
        print(f"video_url: {pkt.video_url}")
    print(f"media_url: {pkt.media_url}")
    if pkt.thumbnail_url and pkt.thumbnail_url != pkt.media_url:
        print(f"thumbnail: {pkt.thumbnail_url}")
    print(pkt.caption)
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = _parse_args()
    platforms = [args.platform] if args.platform else None
    client = HotMeme(
        config_path=CONFIG,
        api_key=_load_api_key(),
        tikhub_enabled=True,
        platforms=platforms,
    )
    effective_platforms = client.platforms
    _print_api_plan(client, effective_platforms)

    packet = client.crawl_once()
    output = client.render_output(packet.fetched_items)
    _print_api_actual(packet.api_calls)

    if not output.packets:
        if packet.fetch_errors:
            for err in packet.fetch_errors:
                print(err, file=sys.stderr)
                print(file=sys.stderr)
            raise SystemExit(1)
        print(
            "未从 TikHub 获取到可展示热帖"
            f"（拉取 {len(packet.fetched_items)} 条，新增 {len(packet.new_items)} 条，"
            f"来源成功: {','.join(packet.providers_ok) or '无'}）",
            file=sys.stderr,
        )
        raise SystemExit(1)

    total = len(output.packets)
    for index, pkt in enumerate(output.packets, start=1):
        _print_packet(index, total, pkt)

    print(
        "summary:",
        f"fetched={len(packet.fetched_items)}",
        f"new={len(packet.new_items)}",
        f"rendered={total}",
        f"api_calls={len(packet.api_calls)}",
        f"providers_ok={','.join(packet.providers_ok)}",
    )
    if args.json:
        print(json.dumps(output.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
