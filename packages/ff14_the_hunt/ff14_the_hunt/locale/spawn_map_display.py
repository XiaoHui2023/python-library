from __future__ import annotations

from ff14_the_hunt.models import RegionMapImage, SpawnMapLayout

_NORM_FORMULA_ZH = "地图X = (格点X - 1) / 格点尺度；地图Y = (格点Y - 1) / 格点尺度"
_NORM_FORMULA_EN = "map_x = (grid_x - 1) / grid_scale; map_y = (grid_y - 1) / grid_scale"
_PIXEL_FORMULA_ZH = "像素X = 地图X × 原图宽；像素Y = 地图Y × 原图高"
_PIXEL_FORMULA_EN = "pixel_x = map_x * image_width; pixel_y = map_y * image_height"


def spawn_layout_to_display_dict(layout: SpawnMapLayout) -> dict[str, object]:
    return {
        "grid_scale": layout.grid_scale,
        "grid_size_x": layout.grid_size_x,
        "grid_size_y": layout.grid_size_y,
        "display_points": layout.display_points,
        "version": layout.version,
        "normalization": _NORM_FORMULA_EN,
        "pixel_mapping": _PIXEL_FORMULA_EN,
    }


def spawn_layout_to_display_dict_zh(layout: SpawnMapLayout) -> dict[str, object]:
    return {
        "格点尺度": layout.grid_scale,
        "格点宽": layout.grid_size_x,
        "格点高": layout.grid_size_y,
        "展示点数": layout.display_points,
        "资源版本": layout.version,
        "归一化": _NORM_FORMULA_ZH,
        "像素映射": _PIXEL_FORMULA_ZH,
    }


def region_map_to_display_dict(
    image: RegionMapImage,
    *,
    embed_data: bool = True,
    file_name: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "region": image.region,
        "source_url": image.source_url,
        "mime_type": image.mime_type,
        "width": image.width,
        "height": image.height,
    }
    if embed_data:
        item["data_base64"] = image.data_base64
    elif file_name is not None:
        item["file_name"] = file_name
    return item


def region_map_to_display_dict_zh(
    image: RegionMapImage,
    *,
    embed_data: bool = True,
    file_name: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "区域": image.region,
        "来源": image.source_url,
        "mime": image.mime_type,
        "宽": image.width,
        "高": image.height,
    }
    if embed_data:
        item["data_base64"] = image.data_base64
    elif file_name is not None:
        item["地图文件"] = file_name
    return item
