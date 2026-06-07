from __future__ import annotations

from typing import Protocol


class _HasConfig(Protocol):
    config: object


def enabled_sources(
    registry: dict[str, _HasConfig],
    *,
    names: list[str] | None = None,
) -> list[str]:
    """返回已启用的来源 ID 列表。"""
    ids: list[str] = []
    for provider_id, source in registry.items():
        if names is not None and provider_id not in names:
            continue
        enabled = getattr(source.config, "enabled", False)
        if not enabled:
            continue
        ids.append(provider_id)
    return ids
