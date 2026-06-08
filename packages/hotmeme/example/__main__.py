import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from hotmeme import HotMeme, supported_platforms
from hotmeme.pipeline.diagnostics import format_fetch_diagnostics, format_materialize_diagnostics
from hotmeme.pipeline.fetch_plan import (
    describe_expected_api_calls,
    local_filter_chain,
    min_expected_call_count,
)
from hotmeme.renderer.delivery import message_from_packet

from example.export_local import export_packet_images, make_run_dir, packet_json_view

EXAMPLE_DIR = Path(__file__).resolve().parent
CONFIG = EXAMPLE_DIR / "config.example.yaml"
OUTPUT_BASE = EXAMPLE_DIR / "output"


def _progress(message: str) -> None:
    print(f"[流程] {message}", flush=True)


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
    print(f"本地后处理：{local_filter_chain()}")
    print("图片下载：在 render_output 阶段，仅对筛选后待渲染条目拉取")
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


def _print_packet(
    index: int,
    total: int,
    pkt,
    *,
    image_local_paths: list[str],
) -> None:
    message = message_from_packet(pkt)
    print(f"--- [{index}/{total}] {pkt.title[:80]} ---")
    print("[一条消息]")
    for image_index, local_path in enumerate(image_local_paths, start=1):
        print(f"图{image_index}: {local_path}")
    if message.text:
        print(message.text)
    print("[参考]")
    if pkt.reference.author:
        print(f"作者: {pkt.reference.author}")
    print(f"链接: {pkt.reference.source_url}")
    if pkt.reference.search_tag:
        print(f"搜索 tag: {pkt.reference.search_tag}")
    if message.images:
        print(f"本条图片数: {len(message.images)}")
    print("[元数据]")
    print(f"platform: {pkt.platform}")
    print(f"score: {pkt.score}")
    print(f"rank_score: {pkt.rank_score:.2f}" if pkt.rank_score is not None else "rank_score: -")
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

    _progress("步骤 1/5：TikHub 拉取与本地筛选…")
    packet = client.crawl_once()
    filtered = len(packet.fetched_items)
    _progress(f"步骤 1/5 完成：筛选后 {filtered} 条")

    _progress("步骤 2/5：下载图片并渲染…")
    output = client.render_output(packet.fetched_items, on_progress=_progress)
    _progress(f"步骤 2/5 完成：渲染 {len(output.packets)} 条")

    _print_api_actual(packet.api_calls)

    _progress("步骤 3/5：打印拉取与下载诊断…")
    if packet.diagnostics is not None:
        for line in format_fetch_diagnostics(packet.diagnostics):
            print(line, flush=True)
    for line in format_materialize_diagnostics(output):
        print(line, flush=True)

    if not output.packets:
        for err in output.materialize_errors:
            print(err, file=sys.stderr)
            print(file=sys.stderr)
        if packet.fetch_errors:
            for err in packet.fetch_errors:
                print(err, file=sys.stderr)
                print(file=sys.stderr)
        if output.materialize_errors or packet.fetch_errors:
            raise SystemExit(1)
        print(
            "未从 TikHub 获取到可展示热帖"
            f"（筛选后 {len(packet.fetched_items)} 条，新增 {len(packet.new_items)} 条，"
            f"来源成功: {','.join(packet.providers_ok) or '无'}）",
            file=sys.stderr,
        )
        raise SystemExit(1)

    _progress("步骤 4/5：写入本地图片文件…")
    run_dir = make_run_dir(OUTPUT_BASE)
    output_dir_label = str(run_dir.relative_to(EXAMPLE_DIR))
    print("=== 本地图片输出 ===", flush=True)
    print(output_dir_label, flush=True)
    print(flush=True)

    total = len(output.packets)
    json_packets: list[dict] = []
    for index, pkt in enumerate(output.packets, start=1):
        _progress(f"  写入帖子 {index}/{total}…")
        image_local_paths = export_packet_images(
            index,
            pkt,
            run_dir,
            path_root=EXAMPLE_DIR,
        )
        _print_packet(
            index,
            total,
            pkt,
            image_local_paths=image_local_paths,
        )
        if args.json:
            json_packets.append(packet_json_view(pkt, image_local_paths))
    _progress(f"步骤 4/5 完成：已写入 {output_dir_label}")

    _progress("步骤 5/5：汇总")
    print(
        "summary:",
        f"fetched={len(packet.fetched_items)}",
        f"new={len(packet.new_items)}",
        f"rendered={total}",
        f"api_calls={len(packet.api_calls)}",
        f"providers_ok={','.join(packet.providers_ok)}",
        f"output_dir={output_dir_label}",
        flush=True,
    )
    if args.json:
        payload = {
            "rendered_at": output.rendered_at.isoformat(),
            "output_dir": output_dir_label,
            "packets": json_packets,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
