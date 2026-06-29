"""从 ffxiv-datamining-mixed 生成 locale/data 下的中英文名对照 JSON。"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ff14_the_hunt import FF14TheHunt
from ff14_the_hunt.common.http_request import DEFAULT_USER_AGENT

DATAMINING_BASE = (
    "https://cdn.jsdelivr.net/gh/InfSein/ffxiv-datamining-mixed@master"
)
OUT_DIR = Path(__file__).resolve().parents[1] / "ff14_the_hunt" / "locale" / "data"

HUNT_PREFIX_ZH: dict[str, str] = {
    "Arch Aethereater": "噬灵王",
    "Ker": "克勒尔",
    "Forgiven Rebellion": "忆罪虚伪神晕",
}


def _download_text(url: str, *, timeout: float = 180.0) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def _load_name_rows(lang: str, sheet: str) -> dict[str, str]:
    url = f"{DATAMINING_BASE}/{lang}/{sheet}"
    text = _download_text(url)
    reader = csv.DictReader(io.StringIO(text))
    rows: dict[str, str] = {}
    for row in reader:
        key = str(row.get("key", "")).strip()
        if not key.isdigit():
            continue
        name = str(row.get("0", "")).strip()
        if name:
            rows[key] = name
    return rows


def _norm_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _build_bnpc_name_map() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    en_rows = _load_name_rows("en", "BNpcName.csv")
    chs_rows = _load_name_rows("chs", "BNpcName.csv")
    en_to_zh: dict[str, str] = {}
    norm_to_en: dict[str, str] = {}
    for key, en_name in en_rows.items():
        zh_name = chs_rows.get(key)
        if zh_name:
            en_to_zh[en_name] = zh_name
        norm_to_en[_norm_name(en_name)] = en_name
    return en_rows, en_to_zh, norm_to_en


def _build_region_map(en_to_zh: dict[str, str]) -> dict[str, str]:
    hunt = FF14TheHunt()
    regions = sorted(
        {
            str(meta.get("Region", "")).strip()
            for meta in hunt.ensure_resources().database_hunt.values()
            if meta.get("Region")
        }
    )
    place_rows_en = _load_name_rows("en", "PlaceName.csv")
    place_rows_chs = _load_name_rows("chs", "PlaceName.csv")
    en_place_to_zh = {
        en_name: place_rows_chs[key]
        for key, en_name in place_rows_en.items()
        if key in place_rows_chs
    }
    region_map: dict[str, str] = {}
    for region in regions:
        if region in en_to_zh:
            region_map[region] = en_to_zh[region]
        elif region in en_place_to_zh:
            region_map[region] = en_place_to_zh[region]
    return region_map


def _resolve_bnpc_en_name(
    hunt_key: str,
    en_to_zh: dict[str, str],
    norm_to_en: dict[str, str],
) -> str | None:
    if hunt_key in en_to_zh:
        return hunt_key
    alias = norm_to_en.get(_norm_name(hunt_key))
    if alias and alias in en_to_zh:
        return alias
    if hunt_key.startswith("The "):
        tail = hunt_key[4:]
        if tail in en_to_zh:
            return tail
        alias = norm_to_en.get(_norm_name(tail))
        if alias and alias in en_to_zh:
            return alias
    return None


def _translate_hunt_key(
    hunt_key: str,
    en_to_zh: dict[str, str],
    norm_to_en: dict[str, str],
) -> str | None:
    for prefix, zh_name in HUNT_PREFIX_ZH.items():
        if hunt_key.startswith(f"{prefix} "):
            return zh_name
    bnpc_name = _resolve_bnpc_en_name(hunt_key, en_to_zh, norm_to_en)
    if bnpc_name is not None:
        return en_to_zh[bnpc_name]
    return None


def _build_hunt_map(
    en_to_zh: dict[str, str],
    norm_to_en: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    hunt = FF14TheHunt()
    hunt_map: dict[str, str] = {}
    missing: list[str] = []
    for hunt_key in hunt.ensure_resources().database_hunt:
        zh_name = _translate_hunt_key(hunt_key, en_to_zh, norm_to_en)
        if zh_name:
            hunt_map[hunt_key] = zh_name
        else:
            missing.append(hunt_key)
    return hunt_map, missing


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _, en_to_zh, norm_to_en = _build_bnpc_name_map()
        region_map = _build_region_map(en_to_zh)
        hunt_map, missing = _build_hunt_map(en_to_zh, norm_to_en)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        return 1

    (OUT_DIR / "regions_zh.json").write_text(
        json.dumps(region_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "hunts_zh.json").write_text(
        json.dumps(hunt_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"regions: {len(region_map)}")
    print(f"hunts: {len(hunt_map)}")
    if missing:
        print(f"missing hunts ({len(missing)}):")
        for name in missing[:20]:
            print(" ", name)
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
