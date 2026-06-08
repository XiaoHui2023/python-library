from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.merge.rank import rank_score
from hotmeme.models import ImageItem, MediaType
from hotmeme.pipeline.fetch_plan import API_LAYER_FILTERS
from hotmeme.post_process import LOCAL_FILTER_CHAIN
from hotmeme.renderer.content import build_post_content, build_post_reference
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


def _primary_image_url(item: ImageItem) -> str:
    if item.image_urls:
        return item.image_urls[0]
    return item.image_url or item.preview_url or ""


def _api_filters_for(item: ImageItem) -> str:
    platform = item.community or ""
    return API_LAYER_FILTERS.get(platform, "")


def render_item(
    item: ImageItem,
    *,
    max_images_per_item: int | None = None,
) -> MemeOutputPacket:
    """把单条热帖项渲染为一条可发送的输出包。"""
    if item.media_type == MediaType.VIDEO and item.video_url:
        media_url = _prefer_openable_video_url(item)
        media_kind = OutputMediaKind.VIDEO
        thumbnail = item.image_url or None
        if not thumbnail and item.preview_url:
            thumbnail = item.preview_url
    else:
        media_url = _primary_image_url(item)
        media_kind = OutputMediaKind.IMAGE
        thumbnail = media_url or None
    content = build_post_content(
        item,
        media_url=media_url,
        max_images_per_item=max_images_per_item,
    )
    return MemeOutputPacket(
        item_id=item.id,
        platform=item.community or "",
        provider=item.provider,
        source_id=item.source_id,
        title=item.title,
        content=content,
        reference=build_post_reference(
            item,
            max_images_per_item=max_images_per_item,
        ),
        media_type=item.media_type.value,
        media_kind=media_kind,
        media_url=media_url,
        image_url=_primary_image_url(item),
        video_url=item.video_url,
        thumbnail_url=thumbnail,
        score=item.score,
        rank_score=rank_score(item),
        created_at=item.created_at,
        nsfw=item.nsfw,
        risk_flags=list(item.risk_flags),
        api_filters=_api_filters_for(item),
        post_filters=LOCAL_FILTER_CHAIN,
    )


def render_items(
    items: list[ImageItem],
    *,
    max_images_per_item: int | None = None,
) -> MemeOutputBatch:
    """批量渲染热帖项；每个 packet 对应一条对外消息。"""
    return MemeOutputBatch(
        packets=[
            render_item(item, max_images_per_item=max_images_per_item)
            for item in items
        ],
        rendered_at=datetime.now(UTC),
    )
