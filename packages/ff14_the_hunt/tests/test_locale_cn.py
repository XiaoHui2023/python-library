from ff14_the_hunt import (
    HuntDisplayLocale,
    HuntQueryFilter,
    HuntRankKind,
    crawl_packet_to_display_dict,
    detect_display_locale,
    normalize_patch_codes,
    query_to_display_dict,
)
from ff14_the_hunt.locale.names import translate_hunt_name, translate_region
from ff14_the_hunt.models import HuntCrawlPacket, HuntMarkRecord


def test_normalize_patch_codes_accepts_chinese_name() -> None:
    assert normalize_patch_codes(["金曦之遗辉"]) == ["DT"]
    assert normalize_patch_codes(["DT", "金曦之遗辉"]) == ["DT"]


def test_query_to_display_dict_uses_chinese_labels() -> None:
    query = HuntQueryFilter(
        data_centers=["猫小胖"],
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S],
        patches=["DT"],
    )
    payload = query_to_display_dict(query)
    assert payload == {
        "数据中心": ["猫小胖"],
        "世界": ["静语庄园"],
        "狩猎等级": ["S级"],
        "资料片": ["金曦之遗辉"],
        "含无计时占位": False,
    }


def test_detect_display_locale_follows_cn_data_center() -> None:
    query = HuntQueryFilter(data_centers=["猫小胖"], worlds=["静语庄园"])
    assert detect_display_locale(query) == HuntDisplayLocale.ZH


def test_detect_display_locale_uses_en_for_aether() -> None:
    query = HuntQueryFilter(data_centers=["Aether"], worlds=["Adamantoise"])
    assert detect_display_locale(query) == HuntDisplayLocale.EN


def test_translate_hunt_and_region_names_for_cn() -> None:
    assert (
        translate_hunt_name("Arch Aethereater Kozama'uka", HuntDisplayLocale.ZH)
        == "噬灵王"
    )
    assert translate_region("Kozama'uka", HuntDisplayLocale.ZH) == "克扎玛乌卡湿地"
    assert (
        translate_hunt_name("Arch Aethereater Kozama'uka", HuntDisplayLocale.EN)
        == "Arch Aethereater Kozama'uka"
    )


def test_crawl_packet_to_display_dict_lists_all_marks() -> None:
    query = HuntQueryFilter(
        data_centers=["猫小胖"],
        worlds=["静语庄园"],
        rank_kinds=[HuntRankKind.S],
        patches=["DT"],
    )
    packet = HuntCrawlPacket(
        crawled_at=1.0,
        marks=[
            HuntMarkRecord(
                hunt_key="Arch Aethereater Kozama'uka",
                hunt_name="Arch Aethereater Kozama'uka",
                world_name="静语庄园",
                region="Kozama'uka",
                patch="DT",
            ),
            HuntMarkRecord(
                hunt_key="Mindflayer",
                hunt_name="Mindflayer",
                world_name="静语庄园",
                region="Middle La Noscea",
                patch="ARR",
            ),
        ],
        query=query,
    )
    payload = crawl_packet_to_display_dict(packet, locale=HuntDisplayLocale.ZH)
    assert payload["配置"]["资料片"] == ["金曦之遗辉"]
    assert len(payload["怪物"]) == 2
    assert payload["怪物"][0]["狩猎名"] == "噬灵王"
    assert payload["怪物"][0]["地图区域"] == "克扎玛乌卡湿地"
    assert payload["怪物"][1]["狩猎名"] == "夺心魔"
