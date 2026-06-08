from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.merge.rank import rank_score
from hotmeme.models import ImageItem, MediaType
from hotmeme.pipeline.fetch_plan import API_LAYER_FILTERS
from hotmeme.post_process import LOCAL_FILTER_CHAIN
from hotmeme.renderer.models import MemeOutputBatch, MemeOutputPacket, OutputMediaKind


_EXPIRING_VIDEO_MARKERS = ("douyinvod.com", "Expires=")


def _prefer_openable_video_url(item: ImageItem) -> str:
    stream = item.video_url or ""
    if stream and not any(marker in stream for marker in _EXPIRING_VIDEO_MARKERS):
        return stream
    for candidate in (item.preview_url, item.source_url, stream):
        if candidate:
            return candidate
    return ""


def _caption_for(item: ImageItem) -> str:
    title = item.title.strip()
    if item.author:
        return f"{title}\n— {item.author}"
    return title


def _api_filters_for(item: ImageItem) -> str:
    platform = item.community or ""
    return API_LAYER_FILTERS.get(platform, "")


def render_item(item: ImageItem) -> MemeOutputPacket:
    """把单条热帖项渲染为输出包。"""
    if item.media_type == MediaType.VIDEO and item.video_url:
        media_url = _prefer_openable_video_url(item)
        media_kind = OutputMediaKind.VIDEO
        thumbnail = item.image_url or None
        if not thumbnail and item.preview_url:
            thumbnail = item.preview_url
    else:
        media_url = item.image_url or item.preview_url or ""
        media_kind = OutputMediaKind.IMAGE
        thumbnail = item.preview_url or item.image_url or None
    return MemeOutputPacket(
        item_id=item.id,
        platform=item.community or "",
        search_tag=item.search_tag,
        provider=item.provider,
        source_id=item.source_id,
        title=item.title,
        caption=_caption_for(item),
        media_type=item.media_type.value,
        media_kind=media_kind,
        media_url=media_url,
        image_url=item.image_url,
        video_url=item.video_url,
        thumbnail_url=thumbnail,
        source_url=item.source_url,
        author=item.author,
        score=item.score,
        rank_score=rank_score(item),
        created_at=item.created_at,
        nsfw=item.nsfw,
        risk_flags=list(item.risk_flags),
        api_filters=_api_filters_for(item),
        post_filters=LOCAL_FILTER_CHAIN,
    )


def render_items(items: list[ImageItem]) -> MemeOutputBatch:
    """批量渲染热帖项。"""
    return MemeOutputBatch(
        packets=[render_item(item) for item in items],
        rendered_at=datetime.now(UTC),
    )
