import base64
import struct
import zlib

from ff14_the_hunt.models import MapCoordinate
from ff14_the_hunt.spawn_map.coordinates import with_pixel_coordinates
from ff14_the_hunt.spawn_map.layout import layout_from_spawn_entry
from ff14_the_hunt.spawn_map.png_meta import read_png_dimensions


def _minimal_png(width: int, height: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_chunk = (
        b"IHDR"
        + ihdr
        + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    )
    ihdr_len = struct.pack(">I", len(ihdr))
    return signature + ihdr_len + ihdr_chunk


def test_read_png_dimensions() -> None:
    data = _minimal_png(2048, 1024)
    assert read_png_dimensions(data) == (2048, 1024)


def test_layout_from_spawn_entry() -> None:
    layout = layout_from_spawn_entry(
        {
            "Dimensions": [41, 41],
            "DisplayPoints": 8,
            "Version": 21,
        },
    )
    assert layout is not None
    assert layout.grid_scale == 41.0
    assert layout.display_points == 8
    assert layout.version == 21


def test_with_pixel_coordinates() -> None:
    points = [
        MapCoordinate(point_key="SpawnPoint01", x=0.5, y=0.25),
    ]
    enriched = with_pixel_coordinates(points, image_width=2000, image_height=1000)
    assert enriched[0].pixel_x == 1000.0
    assert enriched[0].pixel_y == 250.0


def test_build_region_map_image_round_trip() -> None:
    from ff14_the_hunt.spawn_map.region_fetch import RegionMapFetcher
    from ff14_the_hunt.spawn_map.region_image import build_region_map_image

    png = _minimal_png(100, 80)
    fetcher = RegionMapFetcher(site_root="https://tracker.beartoolkit.com")
    fetcher._cache["Shaaloani"] = png
    image = build_region_map_image(region="Shaaloani", fetcher=fetcher)
    assert image is not None
    assert image.width == 100
    assert image.height == 80
    assert base64.b64decode(image.data_base64) == png
