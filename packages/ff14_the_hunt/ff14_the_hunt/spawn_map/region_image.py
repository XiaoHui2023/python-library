from __future__ import annotations

import base64

from ff14_the_hunt.models import RegionMapImage

from ff14_the_hunt.spawn_map.png_meta import read_png_dimensions
from ff14_the_hunt.spawn_map.region_fetch import RegionMapFetcher, region_map_image_url


def build_region_map_image(
    *,
    region: str,
    fetcher: RegionMapFetcher,
) -> RegionMapImage | None:
    """拉取站点区域原图并封装为 ``RegionMapImage``。"""
    source_url = region_map_image_url(fetcher.site_root, region)
    try:
        raw = fetcher.fetch_bytes(region)
        width, height = read_png_dimensions(raw)
    except (RuntimeError, ValueError):
        return None
    return RegionMapImage(
        region=region,
        source_url=source_url,
        mime_type="image/png",
        width=width,
        height=height,
        data_base64=base64.b64encode(raw).decode("ascii"),
    )
