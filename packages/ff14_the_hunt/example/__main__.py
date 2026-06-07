"""示例：中国服务器 · 猫小胖 · 静语庄园 · 7.0（DT）· S 狩猎。

资料片「金曦之遗辉」在 Bear Tracker 内对应 ``Patch=DT``。
示例目标：DT 地图乌克帕夏的 Arch Aethereater Urqopacha（国服常称乌克帕夏 S 链）。
"""

from __future__ import annotations

import json
from pathlib import Path

from ff14_the_hunt import FF14TheHunt, HuntQueryFilter, HuntRankKind

DC_MOOGLE = "\u732b\u5c0f\u80d6"
WORLD_MANOR = "\u9759\u8bed\u5e84\u56ed"
PATCH_DAWNTRAIL = "DT"
EXAMPLE_HUNT = "Arch Aethereater Urqopacha"


def main() -> None:
    hunt = FF14TheHunt()
    print("中国区数据中心:", hunt.list_data_centers(region="CN"))

    query = HuntQueryFilter(
        data_centers=[DC_MOOGLE],
        worlds=[WORLD_MANOR],
        rank_kinds=[HuntRankKind.S],
        patches=[PATCH_DAWNTRAIL],
        hunt_keys=[EXAMPLE_HUNT],
    )

    marks = hunt.query_marks(query, include_spawn_states=True)
    recent = hunt.recently_spawned(query)

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "query": query.model_dump(),
        "marks": [m.model_dump() for m in marks],
        "recently_spawned": [m.model_dump() for m in recent],
    }
    out_path = out_dir / "bear_moogle_manor_dt_s.json"
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"写入 {out_path}")
    for mark in marks:
        print("---")
        print(mark.hunt_name, mark.world_name, mark.region, mark.patch)
        if mark.trigger_timer:
            print("  触发:", mark.trigger_timer.summary)
        if mark.condition_timer:
            print("  条件:", mark.condition_timer.summary)
        if mark.spawn_points:
            pt = mark.spawn_points[0]
            print(
                f"  区域坐标(地图格点): {pt.point_key} "
                f"grid=({pt.grid_x}, {pt.grid_y}) norm=({pt.x:.3f}, {pt.y:.3f})"
            )
        print("  刚刷新:", mark.recently_spawned)

    print(f"同条件下刚刷新 {len(recent)} 条")


if __name__ == "__main__":
    main()
