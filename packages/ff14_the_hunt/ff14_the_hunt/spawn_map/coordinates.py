from __future__ import annotations

from ff14_the_hunt.models import MapCoordinate


def with_pixel_coordinates(
    points: list[MapCoordinate],
    *,
    image_width: int,
    image_height: int,
) -> list[MapCoordinate]:
    """按区域原图像素尺寸补全 ``pixel_x`` / ``pixel_y``。

    Bear Tracker 站点约定：``pixel = norm * image_size``，
    其中 ``norm = (grid - 1) / grid_scale``。
    """
    return [
        point.model_copy(
            update={
                "pixel_x": point.x * image_width,
                "pixel_y": point.y * image_height,
            },
        )
        for point in points
    ]
