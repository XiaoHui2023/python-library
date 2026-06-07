"""示例：中国服务器 · 猫小胖 · 静语庄园 · 金曦之遗辉 · S 狩猎（全部怪物）。"""

from __future__ import annotations

import json
from pathlib import Path

from .spawn_map_io import write_region_map_files

from ff14_the_hunt import (
    FF14TheHunt,
    HuntRankKind,
    crawl_packet_to_display_dict,
    detect_display_locale,
)
from ff14_the_hunt.locale.names import translate_hunt_name, translate_region

DC_MOOGLE = "\u732b\u5c0f\u80d6"
WORLD_MANOR = "\u9759\u8bed\u5e84\u56ed"
PATCH_DAWNTRAIL_CN = "\u91d1\u66e6\u4e4b\u9057\u8f89"


def main() -> None:
    hunt = FF14TheHunt(
        data_centers=[DC_MOOGLE],
        worlds=[WORLD_MANOR],
        rank_kinds=[HuntRankKind.S],
        patches=[PATCH_DAWNTRAIL_CN],
        include_spawn_maps=True,
    )
    print("中国区数据中心:", hunt.list_data_centers(region="CN"))

    packet = hunt.crawl_once()
    marks = packet.marks
    recent = hunt.recently_spawned()

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    region_map_files = write_region_map_files(marks, out_dir)

    locale = detect_display_locale(packet.query)
    payload = crawl_packet_to_display_dict(
        packet,
        recently_spawned=recent,
        locale=locale,
        resources=hunt.ensure_resources(),
        embed_region_map_data=False,
        region_map_file_names=region_map_files,
    )
    out_path = out_dir / "bear_moogle_manor_dt_s.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"写入 {out_path}")
    if region_map_files:
        print(f"区域原图 {len(region_map_files)} 张 -> {out_dir / 'maps'}")
    print(f"配置: {payload['配置']}")
    print(f"共 {len(marks)} 条怪物")
    for mark in marks:
        print("---")
        print(
            translate_hunt_name(mark.hunt_key, locale),
            mark.world_name,
            mark.patch,
            translate_region(mark.region, locale),
        )
        if mark.trigger_timer:
            t = mark.trigger_timer
            print(f"  触发 [{t.bar_color.value} {t.hex_color}]:", t.summary)
        if mark.condition_timer:
            t = mark.condition_timer
            print(f"  条件 [{t.bar_color.value} {t.hex_color}]:", t.summary)
        if mark.fate_timer:
            t = mark.fate_timer
            print(f"  FATE [{t.bar_color.value} {t.hex_color}]:", t.summary)
        if mark.spawn_points:
            pt = mark.spawn_points[0]
            print(
                f"  刷点: {pt.point_key} "
                f"grid=({pt.grid_x}, {pt.grid_y}) "
                f"norm=({pt.x:.3f}, {pt.y:.3f}) "
                f"px=({pt.pixel_x}, {pt.pixel_y})"
            )
        if mark.region_map is not None:
            rel = region_map_files.get((mark.hunt_key, mark.world_name), "")
            print(
                f"  区域原图: {rel} "
                f"({mark.region_map.width}x{mark.region_map.height})"
            )
        print("  刚刷新:", mark.recently_spawned)

    print(f"同条件下刚刷新 {len(recent)} 条")


if __name__ == "__main__":
    main()
