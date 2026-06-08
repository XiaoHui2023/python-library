from __future__ import annotations

from typing import Any

from hotmeme.models import DEFAULT_XHS_SEARCH_TAGS, ImageItem, MediaType
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
    cover = (
        first_url(card.get("cover"))
        or first_url(card.get("image_list"))
        or first_url(card.get("images_list"))
    )
    video_url: str | None = None
    if note_type == "video" or card.get("video") is not None:
        video = card.get("video") if isinstance(card.get("video"), dict) else {}
        video_url = first_url(video.get("media")) or first_url(video)
        media_type = MediaType.VIDEO
    else:
        media_type = MediaType.IMAGE
    image_url = cover
    source_url = f"https://www.xiaohongshu.com/explore/{note_id}"

    interact = card.get("interact_info") if isinstance(card.get("interact_info"), dict) else {}
    score = None
    for key in ("liked_count", "comment_count", "collected_count", "share_count"):
        raw = interact.get(key)
        if isinstance(raw, str) and raw.isdigit():
            score = (score or 0.0) + float(raw)
        elif isinstance(raw, (int, float)):
            score = (score or 0.0) + float(raw)

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


def parse_xhs_search_notes(data: Any) -> list[ImageItem]:
    """解析小红书搜索笔记响应。"""
    items: list[ImageItem] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("note_card", "note"):
                nested = node.get(key)
                if isinstance(nested, dict):
                    parsed = parse_xhs_note_card(nested)
                    if parsed is not None and parsed.id not in seen:
                        seen.add(parsed.id)
                        items.append(parsed)
                    break
            else:
                has_id = "note_id" in node or "id" in node
                has_content = (
                    "display_title" in node
                    or "title" in node
                    or "cover" in node
                    or "images_list" in node
                )
                if has_id and has_content:
                    parsed = parse_xhs_note_card(node)
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
