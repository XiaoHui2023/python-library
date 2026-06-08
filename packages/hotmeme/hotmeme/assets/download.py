from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any

from hotmeme.models import ImageBlob

_DOWNLOAD_HEADERS = {
    "User-Agent": "hotmeme",
    "Accept": "image/*,*/*;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}


class ImageDownloadError(Exception):
    """单张图片下载或校验失败。"""


def _is_image_payload(data: bytes, content_type: str | None) -> bool:
    if len(data) < 12:
        return False
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return True
    if content_type:
        lowered = content_type.lower()
        if lowered.startswith("image/"):
            return True
    return False


def _normalize_content_type(data: bytes, content_type: str | None) -> str | None:
    if content_type:
        lowered = content_type.split(";", 1)[0].strip().lower()
        if lowered.startswith("image/"):
            return lowered
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def fetch_image_bytes(
    url: str,
    *,
    timeout: float,
) -> tuple[bytes, str | None]:
    """下载图片并返回内容与 Content-Type。"""
    request = urllib.request.Request(url, headers=_DOWNLOAD_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ImageDownloadError(f"HTTP {status}")
            content_type = response.headers.get("Content-Type")
            data = response.read()
    except urllib.error.HTTPError as exc:
        raise ImageDownloadError(f"HTTP {exc.code}") from exc
    except TimeoutError as exc:
        raise ImageDownloadError("读取超时") from exc
    except urllib.error.URLError as exc:
        raise ImageDownloadError(str(exc.reason)) from exc
    except OSError as exc:
        raise ImageDownloadError(str(exc)) from exc
    return data, content_type


def download_image(
    url: str,
    *,
    timeout: float,
    min_bytes: int,
) -> ImageBlob:
    """下载单张图片到内存，并校验体积与图片魔数。"""
    data, content_type = fetch_image_bytes(url, timeout=timeout)
    if len(data) < min_bytes:
        raise ImageDownloadError(f"体积过小（{len(data)} 字节）")
    if not _is_image_payload(data, content_type):
        raise ImageDownloadError("响应不是有效图片")
    return ImageBlob(
        data=data,
        content_type=_normalize_content_type(data, content_type),
    )


def item_image_source_urls(item: Any) -> list[str]:
    """收集待下载的远程图片 URL 列表。"""
    urls = list(getattr(item, "image_urls", None) or [])
    if urls:
        return urls
    image_url = getattr(item, "image_url", "") or ""
    if image_url:
        return [image_url]
    return []
