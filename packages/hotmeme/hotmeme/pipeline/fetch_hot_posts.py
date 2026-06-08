from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.common.errors import format_platform_fetch_error
from hotmeme.models import (
    FetchPolicy,
    HotPostsQuery,
    ImageFeed,
    ImageItem,
    PipelinePolicy,
    TikHubApiCall,
    TikHubConfig,
    XiaohongshuPolicy,
)
from hotmeme.post_process import post_process
from hotmeme.sources.tikhub import TikHubSource


def fetch_hot_posts(
    tikhub: TikHubConfig | None,
    pipeline: PipelinePolicy,
    fetch_policy: FetchPolicy,
    query: HotPostsQuery | None = None,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> ImageFeed:
    """TikHub 按平台拉热帖 → 质检。"""
    query = query or HotPostsQuery()
    platforms = query.platforms or pipeline.platforms

    items: list[ImageItem] = []
    ok_ids: list[str] = []
    failed_ids: list[str] = []
    fetch_errors: list[str] = []
    api_calls: list[TikHubApiCall] = []

    if tikhub is None or not tikhub.enabled:
        return ImageFeed(
            items=[],
            fetched_at=datetime.now(UTC),
            providers_ok=ok_ids,
            providers_failed=failed_ids,
            fetch_errors=fetch_errors,
        )

    source = TikHubSource(tikhub)
    if not source.is_implemented:
        failed_ids.append(source.provider_id)
        fetch_errors.append(f"{source.provider_id}: 来源尚未实现")
    else:
        allow_nsfw = query.allow_nsfw if query.allow_nsfw is not None else tikhub.allow_nsfw
        source_ok = False
        for platform in platforms:
            try:
                batch = source.fetch_hot_posts(
                    platform=platform,
                    allow_nsfw=allow_nsfw,
                    xiaohongshu=xiaohongshu,
                )
                items.extend(batch)
                source_ok = True
            except Exception as exc:  # noqa: BLE001
                fetch_errors.append(format_platform_fetch_error(platform, exc))
                continue
        api_calls.extend(source.api_calls)
        if source_ok:
            ok_ids.append(source.provider_id)
        else:
            failed_ids.append(source.provider_id)

    allow_nsfw = query.allow_nsfw if query.allow_nsfw is not None else False
    processed = post_process(
        items,
        allow_nsfw=allow_nsfw,
    )
    return ImageFeed(
        items=processed,
        fetched_at=datetime.now(UTC),
        providers_ok=ok_ids,
        providers_failed=failed_ids,
        fetch_errors=fetch_errors,
        api_calls=api_calls,
    )
