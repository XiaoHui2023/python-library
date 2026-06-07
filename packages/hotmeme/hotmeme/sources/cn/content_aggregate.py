from __future__ import annotations

from hotmeme.cn_models import TopicItem
from hotmeme.models import ImageItem
from hotmeme.common.errors import CnSourceNotImplementedError
from hotmeme.sources.cn.base import BaseContentSource
from hotmeme.sources.cn.registry import enabled_content


def aggregate_search_by_topics(
    registry: dict[str, BaseContentSource],
    topics: list[TopicItem],
    *,
    platforms: list[str],
    images_per_topic: int,
    content_source_names: list[str] | None = None,
    allow_nsfw: bool | None = None,
) -> tuple[list[ImageItem], list[str]]:
    """各内容源按热点独立搜图，再合并。"""
    sources = enabled_content(registry, names=content_source_names)
    items: list[ImageItem] = []
    ok_ids: list[str] = []
    for source in sources:
        if not source.is_implemented:
            continue
        source_ok = False
        for topic in topics:
            for platform in platforms:
                try:
                    batch = source.search_images(
                        topic.title,
                        platform=platform,
                        limit=images_per_topic,
                        topic=topic.title,
                        allow_nsfw=allow_nsfw,
                    )
                    for item in batch:
                        if item.topic is None:
                            item = item.model_copy(update={"topic": topic.title})
                        items.append(item)
                    source_ok = True
                except CnSourceNotImplementedError:
                    continue
                except Exception:  # noqa: BLE001
                    continue
        if source_ok:
            ok_ids.append(source.provider_id)
    return items, ok_ids
