from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hotmeme.models import ImageItem, MediaType
from hotmeme.sources.parsers.common import (
    build_image_item,
    collect_strings,
    first_url,
    parse_created_at,
)


def format_xhs_tag_query(tag: str) -> str:
    """把话题名格式化为小红书搜索用 ``#话题#`` 串。"""
    text = parse_xhs_tag_name(tag)
    if not text:
        return ""
    return f"#{text}#"


def parse_xhs_tag_name(query: str) -> str:
    """从话题名或 ``#话题#`` 搜索串还原为纯 tag 名。"""
    return query.strip().strip("#")


def extract_xhs_hot_keywords(data: Any, *, limit: int) -> list[str]:
    """从小红书热榜响应提取搜索关键词。"""
    return collect_strings(
        data,
        keys=("title", "word", "keyword", "query", "name"),
        limit=limit,
    )


def count_xhs_api_list_items(data: Any) -> int:
    """统计 TikHub 响应里 ``data.items`` 列表长度。"""
    if not isinstance(data, dict):
        return 0
    payload = data.get("data", data)
    if not isinstance(payload, dict):
        return 0
    items = payload.get("items")
    if isinstance(items, list):
        return len(items)
    return 0


def _parse_xhs_count(raw: Any) -> float | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None
    text = raw.strip().replace(",", "")
    if not text:
        return None
    if text.isdigit():
        return float(text)
    if text.endswith("万"):
        head = text[:-1].strip()
        try:
            return float(head) * 10_000.0
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _image_list_entry_url(entry: dict[str, Any]) -> str:
    url = first_url(entry.get("url_size_large")) or first_url(entry.get("url"))
    if url:
        return url
    info = entry.get("info_list")
    if isinstance(info, list):
        return first_url(info)
    return ""


def _extract_xhs_image_urls(card: dict[str, Any]) -> list[str]:
    """按图集顺序收集笔记全部图片 URL。"""
    urls: list[str] = []
    seen: set[str] = set()
    for key in ("images_list", "image_list"):
        entries = card.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = _image_list_entry_url(entry)
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
    if urls:
        return urls
    cover = _extract_xhs_cover(card)
    if cover:
        return [cover]
    return []


def _extract_xhs_cover(card: dict[str, Any]) -> str:
    for key in ("cover", "cover_info", "image_info", "thumb", "default_cover"):
        url = first_url(card.get(key))
        if url:
            return url
    for key in ("image_list", "images_list"):
        entries = card.get(key)
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    url = _image_list_entry_url(entry)
                    if url:
                        return url
        url = first_url(entries)
        if url:
            return url
    v2 = card.get("video_info_v2")
    if isinstance(v2, dict):
        image = v2.get("image")
        if isinstance(image, dict):
            for key in ("thumbnail", "thumbnail_dim", "first_frame", "url"):
                url = first_url(image.get(key))
                if url:
                    return url
    return ""


def _stream_entry_video_url(entry: dict[str, Any]) -> str:
    for key in ("master_url", "url"):
        raw = entry.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return first_url(entry.get("backup_urls"))


def _extract_xhs_stream_video_url(stream: Any) -> str:
    if not isinstance(stream, dict):
        return ""
    for codec in ("h264", "h265", "av1"):
        entries = stream.get(codec)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = _stream_entry_video_url(entry)
            if url:
                return url
    return ""


def _extract_xhs_video_url(card: dict[str, Any]) -> str:
    video = card.get("video")
    if isinstance(video, dict):
        media = video.get("media")
        if isinstance(media, dict):
            url = _extract_xhs_stream_video_url(media.get("stream"))
            if url:
                return url
        url = first_url(media) or first_url(video)
        if url:
            return url
    v2 = card.get("video_info_v2")
    if not isinstance(v2, dict):
        return ""
    media = v2.get("media")
    if not isinstance(media, dict):
        return ""
    url = _extract_xhs_stream_video_url(media.get("stream"))
    if url:
        return url
    video_node = media.get("video")
    if isinstance(video_node, dict):
        opaque = video_node.get("opaque1")
        if isinstance(opaque, dict):
            for key in (
                "default_screencast_stream",
                "hd_screencast_stream",
                "hd_screencast_stream_basic",
            ):
                raw = opaque.get(key)
                if isinstance(raw, str) and raw.strip():
                    return raw.strip()
    return ""


_XHS_SCORE_FIELD_KEYS = (
    "liked_count",
    "comment_count",
    "comments_count",
    "collected_count",
    "share_count",
    "shared_count",
)


def _merge_xhs_search_wrapper(wrapper: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    """把 ``items[]`` 外层上的互动字段并入内层 note 卡片。"""
    if wrapper is card:
        return card
    merged = dict(card)
    wrapper_interact = wrapper.get("interact_info")
    card_interact = merged.get("interact_info")
    if isinstance(wrapper_interact, dict):
        if isinstance(card_interact, dict):
            combined = dict(wrapper_interact)
            for key, value in card_interact.items():
                if key not in combined or _parse_xhs_count(combined.get(key)) is None:
                    combined[key] = value
            merged["interact_info"] = combined
        else:
            merged["interact_info"] = dict(wrapper_interact)
    for key in _XHS_SCORE_FIELD_KEYS:
        if key in wrapper and _parse_xhs_count(merged.get(key)) is None:
            if _parse_xhs_count(wrapper.get(key)) is not None:
                merged[key] = wrapper[key]
    return merged


def _extract_xhs_score(card: dict[str, Any]) -> float | None:
    score: float | None = None
    sources: list[dict[str, Any]] = []
    interact = card.get("interact_info")
    if isinstance(interact, dict):
        sources.append(interact)
    sources.append(card)
    for source in sources:
        for key in _XHS_SCORE_FIELD_KEYS:
            parsed = _parse_xhs_count(source.get(key))
            if parsed is not None:
                score = (score or 0.0) + parsed
    return score


def _note_card_dict(node: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("note_card", "note"):
        nested = node.get(key)
        if isinstance(nested, dict):
            return nested
    has_id = "note_id" in node or "id" in node
    has_content = any(
        key in node
        for key in (
            "display_title",
            "title",
            "desc",
            "cover",
            "cover_info",
            "image_list",
            "images_list",
            "image_info",
            "video",
            "video_info_v2",
        )
    )
    if has_id and has_content:
        return node
    return None


def _xhs_card_has_media(card: dict[str, Any]) -> bool:
    """笔记卡片是否含可解析的图或视频 URL。"""
    return bool(_extract_xhs_cover(card) or _extract_xhs_video_url(card))


def _collect_xhs_search_note_cards(data: Any) -> list[dict[str, Any]]:
    """从 search_notes 响应收集笔记卡片（先走 items 直取，再递归兜底）。"""
    cards: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def add_card(card: dict[str, Any]) -> None:
        note_id = str(card.get("note_id") or card.get("id") or "")
        if note_id and note_id in seen_ids:
            return
        if note_id:
            seen_ids.add(note_id)
        cards.append(card)

    def from_items(items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            card = _note_card_dict(item)
            if card is not None:
                if card is not item:
                    card = _merge_xhs_search_wrapper(item, card)
                add_card(card)

    if isinstance(data, dict):
        from_items(data.get("items"))
        payload = data.get("data")
        if isinstance(payload, dict):
            from_items(payload.get("items"))
            inner = payload.get("data")
            if isinstance(inner, dict):
                from_items(inner.get("items"))

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            card = _note_card_dict(node)
            if card is not None:
                if card is not node:
                    card = _merge_xhs_search_wrapper(node, card)
                add_card(card)
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(data)
    return cards


@dataclass
class XhsParseRunStats:
    """单次 search_notes 响应解析统计。"""

    api_list_items: int = 0
    note_candidates: int = 0
    parsed_with_media: int = 0
    no_media: int = 0


def parse_xhs_note_card(card: dict[str, Any]) -> ImageItem | None:
    """把单条小红书笔记卡片解析为 ``ImageItem``。"""
    note_id = str(card.get("note_id") or card.get("id") or "")
    if not note_id:
        return None
    headline = str(card.get("display_title") or card.get("title") or "").strip()
    body = str(card.get("desc") or "").strip()
    title = headline or body or "热帖"
    note_body = body if body and body != headline else None
    user = card.get("user") if isinstance(card.get("user"), dict) else {}
    author = str(user.get("nickname") or user.get("name") or "") or None
    image_urls = _extract_xhs_image_urls(card)
    if not image_urls:
        return None
    cover = image_urls[0]
    source_url = f"https://www.xiaohongshu.com/explore/{note_id}"
    score = _extract_xhs_score(card)

    return build_image_item(
        provider="tikhub",
        platform="xiaohongshu",
        source_id=note_id,
        title=title,
        body=note_body,
        image_urls=image_urls,
        image_url=cover,
        video_url=None,
        preview_url=cover,
        source_url=source_url,
        author=author,
        score=score,
        created_at=parse_created_at(card.get("time") or card.get("create_time")),
        media_type=MediaType.IMAGE,
    )


def parse_xhs_search_notes_traced(
    data: Any,
) -> tuple[list[ImageItem], XhsParseRunStats]:
    """解析小红书搜索笔记响应，并返回统计。"""
    stats = XhsParseRunStats(api_list_items=count_xhs_api_list_items(data))
    items: list[ImageItem] = []
    seen: set[str] = set()

    for card in _collect_xhs_search_note_cards(data):
        note_id = str(card.get("note_id") or card.get("id") or "")
        if note_id:
            stats.note_candidates += 1
        parsed = parse_xhs_note_card(card)
        if parsed is None:
            if note_id:
                stats.no_media += 1
            continue
        if parsed.id in seen:
            continue
        seen.add(parsed.id)
        stats.parsed_with_media += 1
        items.append(parsed)

    return items, stats


def parse_xhs_search_notes(data: Any) -> list[ImageItem]:
    """解析小红书搜索笔记响应。"""
    items, _stats = parse_xhs_search_notes_traced(data)
    return items
