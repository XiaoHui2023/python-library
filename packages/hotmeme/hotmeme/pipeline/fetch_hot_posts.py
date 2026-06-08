from __future__ import annotations



from datetime import UTC, datetime



from hotmeme.common.errors import format_platform_fetch_error
from hotmeme.models import (
    FetchDiagnostics,
    FetchPolicy,
    HotPostsQuery,
    ImageFeed,
    ImageItem,
    PipelinePolicy,
    TikHubApiCall,
    TikHubConfig,
    XiaohongshuPolicy,
)
from hotmeme.pipeline.diagnostics import post_process_traced
from hotmeme.policy.min_score import resolve_platform_min_scores

from hotmeme.sources.tikhub import TikHubSource





def fetch_hot_posts(

    tikhub: TikHubConfig | None,

    pipeline: PipelinePolicy,

    fetch_policy: FetchPolicy,

    query: HotPostsQuery | None = None,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> ImageFeed:

    """TikHub 按平台拉热帖并本地筛选（不下载图片）。"""

    query = query or HotPostsQuery()

    platforms = query.platforms or pipeline.platforms



    items: list[ImageItem] = []

    ok_ids: list[str] = []

    failed_ids: list[str] = []

    fetch_errors: list[str] = []

    api_calls: list[TikHubApiCall] = []

    xhs_keyword_stats = []



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

                result = source.fetch_platform_result(

                    platform=platform,

                    allow_nsfw=allow_nsfw,

                    xiaohongshu=xiaohongshu,

                )

                items.extend(result.items)

                xhs_keyword_stats.extend(result.xhs_keyword_stats)

                source_ok = True

            except Exception as exc:  # noqa: BLE001

                fetch_errors.append(format_platform_fetch_error(platform, exc))

                continue

        api_calls.extend(source.api_calls)

        if source_ok:

            ok_ids.append(source.provider_id)

        else:

            failed_ids.append(source.provider_id)



    allow_nsfw = (
        query.allow_nsfw
        if query.allow_nsfw is not None
        else (tikhub.allow_nsfw if tikhub is not None else False)
    )
    media_types = tikhub.media_types if tikhub is not None else None

    parsed_before = len(items)
    platform_min_scores = resolve_platform_min_scores(
        platforms,
        xiaohongshu=xiaohongshu,
    )
    processed, post_stages = post_process_traced(
        items,
        allow_nsfw=allow_nsfw,
        media_types=media_types,
        platform_min_scores=platform_min_scores,
    )

    diagnostics = FetchDiagnostics(
        parsed_before_filter=parsed_before,
        final_count=len(processed),
        xhs_keywords=xhs_keyword_stats,
        post_process=post_stages,
    )

    return ImageFeed(
        items=processed,

        fetched_at=datetime.now(UTC),

        providers_ok=ok_ids,

        providers_failed=failed_ids,

        fetch_errors=fetch_errors,

        api_calls=api_calls,

        diagnostics=diagnostics,

    )


