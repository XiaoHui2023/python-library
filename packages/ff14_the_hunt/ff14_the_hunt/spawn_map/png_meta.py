from __future__ import annotations

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_png_dimensions(data: bytes) -> tuple[int, int]:
    """从 PNG 文件头读取宽高（无需图像库）。

    Args:
        data: PNG 文件字节。

    Returns:
        ``(width, height)`` 像素。

    Raises:
        ValueError: 非 PNG 或数据过短。
    """
    if len(data) < 24 or data[:8] != _PNG_SIGNATURE:
        raise ValueError("invalid PNG data")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise ValueError("invalid PNG dimensions")
    return width, height
