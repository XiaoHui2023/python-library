from __future__ import annotations

from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.locale import cn as zh_display
from ff14_the_hunt.locale import en as en_display
from ff14_the_hunt.locale.detect import detect_display_locale
from ff14_the_hunt.locale.tag import HuntDisplayLocale
from ff14_the_hunt.models import HuntCrawlPacket, HuntMarkRecord, HuntQueryFilter


def query_to_display_dict(
    query: HuntQueryFilter,
    *,
    locale: HuntDisplayLocale | None = None,
) -> dict[str, object]:
    active_locale = locale or detect_display_locale(query)
    if active_locale == HuntDisplayLocale.ZH:
        return zh_display.query_to_display_dict(query)
    return en_display.query_to_display_dict(query)


def mark_to_display_dict(
    mark: HuntMarkRecord,
    *,
    locale: HuntDisplayLocale | None = None,
    embed_region_map_data: bool = True,
    region_map_file_name: str | None = None,
) -> dict[str, object]:
    active_locale = locale or HuntDisplayLocale.ZH
    if active_locale == HuntDisplayLocale.ZH:
        return zh_display.mark_to_display_dict(
            mark,
            embed_region_map_data=embed_region_map_data,
            region_map_file_name=region_map_file_name,
        )
    return en_display.mark_to_display_dict(
        mark,
        embed_region_map_data=embed_region_map_data,
        region_map_file_name=region_map_file_name,
    )


def crawl_packet_to_display_dict(
    packet: HuntCrawlPacket,
    *,
    recently_spawned: list[HuntMarkRecord] | None = None,
    locale: HuntDisplayLocale | None = None,
    resources: BearResources | None = None,
    embed_region_map_data: bool = True,
    region_map_file_names: dict[tuple[str, str], str] | None = None,
) -> dict[str, object]:
    """将单次爬取结果序列化为展示视图；语言默认跟随筛选条件中的服务器区域。"""
    active_locale = locale or detect_display_locale(packet.query, resources=resources)
    if active_locale == HuntDisplayLocale.ZH:
        return zh_display.crawl_packet_to_display_dict(
            packet,
            recently_spawned=recently_spawned,
            embed_region_map_data=embed_region_map_data,
            region_map_file_names=region_map_file_names,
        )
    return en_display.crawl_packet_to_display_dict(
        packet,
        recently_spawned=recently_spawned,
        embed_region_map_data=embed_region_map_data,
        region_map_file_names=region_map_file_names,
    )
