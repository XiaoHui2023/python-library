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


def _extract_xhs_cover(card: dict[str, Any]) -> str:
    for key in ("cover", "cover_info", "image_info", "thumb", "default_cover"):
        url = first_url(card.get(key))
        if url:
            return url
    for key in ("image_list", "images_list"):
        url = first_url(card.get(key))
        if url:
            return url
    return ""


def _extract_xhs_score(card: dict[str, Any]) -> float | None:
    score: float | None = None
    sources: list[dict[str, Any]] = []
    interact = card.get("interact_info")
    if isinstance(interact, dict):
        sources.append(interact)
    sources.append(card)
    for source in sources:
        for key in ("liked_count", "comment_count", "collected_count", "share_count"):
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
        )
    )
    if has_id and has_content:
        return node
    return None


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
    title = str(
        card.get("display_title")
        or card.get("title")
        or card.get("desc")
        or "",
    ).strip()
    user = card.get("user") if isinstance(card.get("user"), dict) else {}
    author = str(user.get("nickname") or user.get("name") or "") or None
    note_type = str(card.get("type") or "").lower()
    cover = _extract_xhs_cover(card)
    video_url: str | None = None
    if note_type == "video" or card.get("video") is not None:
        video = card.get("video") if isinstance(card.get("video"), dict) else {}
        video_url = first_url(video.get("media")) or first_url(video)
        media_type = MediaType.VIDEO
    else:
        media_type = MediaType.IMAGE
    image_url = cover
    source_url = f"https://www.xiaohongshu.com/explore/{note_id}"
    score = _extract_xhs_score(card)

    return build_image_item(
        provider="tikhub",
        platform="xiaohongshu",
        source_id=note_id,
        title=title,
        image_url=image_url,
        video_url=video_url,
        preview_url=cover or None,
        source_url=source_url,
        author=author,
        score=score,
        created_at=parse_created_at(card.get("time") or card.get("create_time")),
        media_type=media_type,
    )


def parse_xhs_search_notes_traced(
    data: Any,
) -> tuple[list[ImageItem], XhsParseRunStats]:
    """解析小红书搜索笔记响应，并返回统计。"""
    stats = XhsParseRunStats(api_list_items=count_xhs_api_list_items(data))
    items: list[ImageItem] = []
    seen: set[str] = set()
    candidate_ids: set[str] = set()

    def _record_candidate(card: dict[str, Any]) -> str:
        note_id = str(card.get("note_id") or card.get("id") or "")
        if note_id and note_id not in candidate_ids:
            candidate_ids.add(note_id)
            stats.note_candidates += 1
        return note_id

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            card = _note_card_dict(node)
            if card is not None:
                note_id = _record_candidate(card)
                parsed = parse_xhs_note_card(card)
                if parsed is None:
                    if note_id:
                        stats.no_media += 1
                elif parsed.id not in seen:
                    seen.add(parsed.id)
                    stats.parsed_with_media += 1
                    items.append(parsed)
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(data)
    return items, stats


def parse_xhs_search_notes(data: Any) -> list[ImageItem]:
    """解析小红书搜索笔记响应。"""
    items, _stats = parse_xhs_search_notes_traced(data)
    return items
