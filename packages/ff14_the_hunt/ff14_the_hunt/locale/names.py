from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources

from ff14_the_hunt.locale.tag import HuntDisplayLocale


@lru_cache(maxsize=1)
def _hunt_names_zh() -> dict[str, str]:
    text = resources.files("ff14_the_hunt.locale.data").joinpath("hunts_zh.json").read_text(
        encoding="utf-8",
    )
    return json.loads(text)


@lru_cache(maxsize=1)
def _region_names_zh() -> dict[str, str]:
    text = resources.files("ff14_the_hunt.locale.data").joinpath(
        "regions_zh.json",
    ).read_text(encoding="utf-8")
    return json.loads(text)


def translate_hunt_name(hunt_key: str, locale: HuntDisplayLocale) -> str:
    if locale == HuntDisplayLocale.EN:
        return hunt_key
    return _hunt_names_zh().get(hunt_key, hunt_key)


def translate_region_name(region: str, locale: HuntDisplayLocale) -> str:
    if locale == HuntDisplayLocale.EN:
        return region
    return _region_names_zh().get(region, region)


def translate_region(region: str | list[str], locale: HuntDisplayLocale) -> str:
    if isinstance(region, list):
        parts = [translate_region_name(item, locale) for item in region]
        separator = "、" if locale == HuntDisplayLocale.ZH else ", "
        return separator.join(parts)
    return translate_region_name(region, locale)
