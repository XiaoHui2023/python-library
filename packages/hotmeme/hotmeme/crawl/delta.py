from __future__ import annotations

from hotmeme.cn_models import TopicItem
from hotmeme.models import ImageItem


def partition_new_images(
    items: list[ImageItem],
    seen_ids: set[str],
) -> list[ImageItem]:
    """保留尚未出现过的图片项（按 ``ImageItem.id``）。"""
    new_items: list[ImageItem] = []
    for item in items:
        if item.id in seen_ids:
            continue
        new_items.append(item)
        seen_ids.add(item.id)
    return new_items


def partition_new_topics(
    topics: list[TopicItem],
    seen_ids: set[str],
) -> list[TopicItem]:
    """保留尚未出现过的热点项（按 ``TopicItem.id``）。"""
    new_topics: list[TopicItem] = []
    for topic in topics:
        if topic.id in seen_ids:
            continue
        new_topics.append(topic)
        seen_ids.add(topic.id)
    return new_topics


def dedupe_images_by_id(items: list[ImageItem]) -> list[ImageItem]:
    """同轮合并多源结果时按 id 去重。"""
    seen: set[str] = set()
    kept: list[ImageItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        kept.append(item)
    return kept
