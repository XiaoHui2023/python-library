from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from hotmeme.models import ImageItem


def normalize_image_url(url: str) -> str:
    """URL 归一化：去 fragment、排序 query、统一小写 host。"""
    parsed = urlparse(url.strip())
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", query, ""))


def dedup_by_url(items: list[ImageItem]) -> list[ImageItem]:
    """按归一化图片 URL 去重，保留先出现的项。"""
    seen: set[str] = set()
    kept: list[ImageItem] = []
    for item in items:
        media_url = item.video_url or item.image_url
        key = normalize_image_url(media_url)
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


def dedup_by_title(items: list[ImageItem]) -> list[ImageItem]:
    """按标题折叠去重（MVP 辅助）。"""
    seen: set[str] = set()
    kept: list[ImageItem] = []
    for item in items:
        title_key = " ".join(item.title.lower().split())
        if not title_key:
            kept.append(item)
            continue
        if title_key in seen:
            continue
        seen.add(title_key)
        kept.append(item)
    return kept


def dedup_items(items: list[ImageItem]) -> list[ImageItem]:
    """URL 去重后再做标题去重。"""
    return dedup_by_title(dedup_by_url(items))
