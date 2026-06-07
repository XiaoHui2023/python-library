from __future__ import annotations

from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.locale.tag import HuntDisplayLocale
from ff14_the_hunt.models import HuntQueryFilter


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def detect_display_locale(
    query: HuntQueryFilter,
    *,
    resources: BearResources | None = None,
) -> HuntDisplayLocale:
    """按筛选条件推断展示语言：中国区数据中心或世界名为中文，否则为英文。"""
    if resources is not None:
        for data_center in query.data_centers:
            info = resources.data_centers.get(data_center, {})
            if info.get("Region") == "CN":
                return HuntDisplayLocale.ZH
    for data_center in query.data_centers:
        if _contains_cjk(data_center):
            return HuntDisplayLocale.ZH
    for world in query.worlds:
        if _contains_cjk(world):
            return HuntDisplayLocale.ZH
    for patch in query.patches:
        if _contains_cjk(patch):
            return HuntDisplayLocale.ZH
    for region in query.regions:
        if _contains_cjk(region):
            return HuntDisplayLocale.ZH
    return HuntDisplayLocale.EN
