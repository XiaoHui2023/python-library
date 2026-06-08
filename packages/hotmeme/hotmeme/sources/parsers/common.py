from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

from hotmeme.common.ids import make_item_id
from hotmeme.common.media import guess_media_type
from hotmeme.models import ImageItem, MediaType


def first_url(value: Any) -> str:
    """从 TikHub 常见 URL 结构取第一个可用地址。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for entry in value:
            url = first_url(entry)
            if url:
                return url
        return ""
    if isinstance(value, dict):
        for key in ("url", "url_default", "url_pre", "origin", "src"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        for key in ("url_list", "urls"):
            nested = value.get(key)
            url = first_url(nested)
            if url:
                return url
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                url = first_url(nested)
                if url:
                    return url
    return ""


def parse_created_at(raw: Any) -> datetime | None:
    """解析平台时间字段。"""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 1_000_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=UTC)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_created_at(int(text))
        try:
            return parsedate_to_datetime(text).astimezone(UTC)
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            return None
    return None


def collect_strings(data: Any, *, keys: tuple[str, ...], limit: int) -> list[str]:
    """从嵌套结构收集指定键的非空字符串。"""
    found: list[str] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if len(found) >= limit:
            return
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    text = str(node[key]).strip()
                    if text and text not in seen:
                        seen.add(text)
                        found.append(text)
                        if len(found) >= limit:
                            return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(data)
    return found


def build_image_item(
    *,
    provider: str,
    platform: str,
    source_id: str,
    title: str,
    body: str | None = None,
    image_urls: list[str] | None = None,
    image_url: str = "",
    video_url: str | None = None,
    preview_url: str | None = None,
    source_url: str,
    author: str | None = None,
    score: float | None = None,
    created_at: datetime | None = None,
    media_type: MediaType | None = None,
    nsfw: bool = False,
    width: int | None = None,
    height: int | None = None,
) -> ImageItem | None:
    """组装 ``ImageItem``；无法判定媒体时返回 ``None``。"""
    title = title.strip()
    if not title:
        title = "热帖"
    if media_type is None:
        if video_url:
            media_type = MediaType.VIDEO
        elif image_url:
            media_type = guess_media_type(image_url)
        else:
            return None
    if media_type == MediaType.VIDEO and not video_url:
        return None
    if media_type != MediaType.VIDEO and not image_url and not video_url:
        return None
    media_key = video_url or image_url or preview_url or source_id
    return ImageItem(
        id=make_item_id(provider=provider, source_id=source_id, image_url=media_key),
        provider=provider,
        source_id=source_id,
        title=title,
        body=body,
        image_urls=list(image_urls or []),
        image_url=image_url,
        video_url=video_url,
        preview_url=preview_url,
        source_url=source_url,
        author=author,
        community=platform,
        score=score,
        created_at=created_at,
        media_type=media_type,
        nsfw=nsfw,
        width=width,
        height=height,
    )
