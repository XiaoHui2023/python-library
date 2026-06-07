from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.cn_models import (
    CnHotQuery,
    CnPipelinePolicy,
    CnSourcesConfig,
    DiscoverTopicsQuery,
)
from hotmeme.models import FetchPolicy, ImageFeed
from hotmeme.post_process import post_process_cn
from hotmeme.sources.cn.content_aggregate import aggregate_search_by_topics
from hotmeme.sources.cn.discovery_aggregate import aggregate_discover
from hotmeme.sources.cn.registry import build_cn_content, build_cn_discovery


def fetch_cn_hot(
    cn_config: CnSourcesConfig,
    pipeline: CnPipelinePolicy,
    fetch_policy: FetchPolicy,
    query: CnHotQuery | None = None,
) -> ImageFeed:
    """发现源聚合热点 → 内容源按热词搜图 → 合并。"""
    query = query or CnHotQuery()
    discovery_registry = build_cn_discovery(cn_config)
    topic_feed = aggregate_discover(
        discovery_registry,
        query=DiscoverTopicsQuery(
            platforms=query.platforms,
            limit=query.topic_limit or pipeline.topic_limit,
            sources=query.discovery_sources,
        ),
        classify=pipeline.classify_topics,
    )

    content_registry = build_cn_content(cn_config)
    search_items, content_ok = aggregate_search_by_topics(
        content_registry,
        topic_feed.topics[: pipeline.topic_limit],
        platforms=pipeline.content_platforms,
        images_per_topic=pipeline.images_per_topic,
        content_source_names=query.content_sources,
        allow_nsfw=query.allow_nsfw,
    )

    content_failed = [
        provider_id
        for provider_id, source in content_registry.items()
        if source.config.enabled and not source.is_implemented
    ]
    failed = list(dict.fromkeys(topic_feed.providers_failed + content_failed))
    ok_ids = list(dict.fromkeys(topic_feed.providers_ok + content_ok))
    allow_nsfw = query.allow_nsfw if query.allow_nsfw is not None else False
    total_limit = query.limit or fetch_policy.total_limit
    processed = post_process_cn(
        search_items,
        allow_nsfw=allow_nsfw,
        total_limit=total_limit,
    )
    return ImageFeed(
        items=processed,
        fetched_at=datetime.now(UTC),
        providers_ok=ok_ids,
        providers_failed=failed,
    )
