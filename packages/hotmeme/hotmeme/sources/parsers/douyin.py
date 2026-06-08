from __future__ import annotations

from typing import Any

from hotmeme.models import ImageItem, MediaType
from hotmeme.sources.parsers.common import (
    build_image_item,
    collect_strings,
    first_url,
    parse_created_at,
)


def extract_douyin_hot_keywords(data: Any, *, limit: int) -> list[str]:
    """从抖音热榜响应提取搜索关键词。"""
    return collect_strings(
        data,
        keys=("word", "keyword", "title", "sentence"),
        limit=limit,
    )


def parse_douyin_aweme(aweme: dict[str, Any]) -> ImageItem | None:
    """把单条抖音作品解析为 ``ImageItem``。"""
    source_id = str(aweme.get("aweme_id") or aweme.get("id") or aweme.get("group_id") or "")
    if not source_id:
        return None
    title = str(aweme.get("desc") or aweme.get("title") or "").strip()
    author_info = aweme.get("author") if isinstance(aweme.get("author"), dict) else {}
    author = str(author_info.get("nickname") or author_info.get("unique_id") or "") or None
    video = aweme.get("video") if isinstance(aweme.get("video"), dict) else {}
    video_url = first_url(video.get("play_addr")) or first_url(video.get("download_addr"))
    cover = first_url(video.get("cover")) or first_url(video.get("origin_cover"))
    image_url = cover
    media_type = MediaType.VIDEO if video_url else MediaType.IMAGE
    source_url = f"https://www.douyin.com/video/{source_id}"

    statistics = aweme.get("statistics") if isinstance(aweme.get("statistics"), dict) else {}
    score = None
    for key in ("digg_count", "comment_count", "share_count", "play_count"):
        value = statistics.get(key)
        if isinstance(value, (int, float)):
            score = (score or 0.0) + float(value)

    width = video.get("width") if isinstance(video.get("width"), int) else None
    height = video.get("height") if isinstance(video.get("height"), int) else None

    return build_image_item(
        provider="tikhub",
        platform="douyin",
        source_id=source_id,
        title=title,
        image_url=image_url,
        video_url=video_url or None,
        preview_url=cover or None,
        source_url=source_url,
        author=author,
        score=score,
        created_at=parse_created_at(aweme.get("create_time")),
        media_type=media_type,
        width=width,
        height=height,
    )


def parse_douyin_video_search(data: Any) -> list[ImageItem]:
    """解析抖音视频搜索响应。"""
    items: list[ImageItem] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            aweme = node.get("aweme_info")
            if isinstance(aweme, dict):
                parsed = parse_douyin_aweme(aweme)
                if parsed is not None and parsed.id not in seen:
                    seen.add(parsed.id)
                    items.append(parsed)
            elif "aweme_id" in node or ("desc" in node and "video" in node):
                parsed = parse_douyin_aweme(node)
                if parsed is not None and parsed.id not in seen:
                    seen.add(parsed.id)
                    items.append(parsed)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(data)
    return items
