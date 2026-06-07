from __future__ import annotations

from datetime import UTC, datetime

from hotmeme.cn_models import DiscoverTopicsQuery, TopicFeed, TopicItem
from hotmeme.sources.cn.base import BaseDiscoverySource
from hotmeme.sources.cn.classify import annotate_topics
from hotmeme.sources.cn.registry import enabled_discovery


def aggregate_discover(
    registry: dict[str, BaseDiscoverySource],
    *,
    query: DiscoverTopicsQuery | None = None,
    classify: bool = True,
) -> TopicFeed:
    """各发现源独立拉榜，再合并热点列表。"""
    query = query or DiscoverTopicsQuery()
    sources = enabled_discovery(registry, names=query.sources)
    topics: list[TopicItem] = []
    ok_ids: list[str] = []
    failed_ids: list[str] = []
    for source in sources:
        try:
            batch = source.discover(
                platforms=query.platforms,
                limit=query.limit,
            )
            topics.extend(batch)
            ok_ids.append(source.provider_id)
        except Exception:  # noqa: BLE001
            failed_ids.append(source.provider_id)
    if classify:
        topics = annotate_topics(topics)
    return TopicFeed(
        topics=topics,
        fetched_at=datetime.now(UTC),
        providers_ok=ok_ids,
        providers_failed=failed_ids,
    )
