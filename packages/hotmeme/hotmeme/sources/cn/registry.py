from __future__ import annotations

from hotmeme.cn_models import CnSourcesConfig
from hotmeme.sources._enabled import enabled_sources as _enabled_ids
from hotmeme.sources.cn.base import BaseContentSource, BaseDiscoverySource
from hotmeme.sources.cn.content.tikhub import TikHubSource
from hotmeme.sources.cn.discovery.hotpush import HotpushSource

DISCOVERY_BUILDERS: dict[str, type[BaseDiscoverySource]] = {
    "hotpush": HotpushSource,
}

CONTENT_BUILDERS: dict[str, type[BaseContentSource]] = {
    "tikhub": TikHubSource,
}


def build_cn_discovery(config: CnSourcesConfig) -> dict[str, BaseDiscoverySource]:
    registry: dict[str, BaseDiscoverySource] = {}
    for key, cls in DISCOVERY_BUILDERS.items():
        section = getattr(config, key, None)
        if section is not None:
            registry[key] = cls(section)  # type: ignore[call-arg]
    return registry


def build_cn_content(config: CnSourcesConfig) -> dict[str, BaseContentSource]:
    registry: dict[str, BaseContentSource] = {}
    for key, cls in CONTENT_BUILDERS.items():
        section = getattr(config, key, None)
        if section is not None:
            registry[key] = cls(section)  # type: ignore[call-arg]
    return registry


def enabled_discovery(
    registry: dict[str, BaseDiscoverySource],
    *,
    names: list[str] | None = None,
) -> list[BaseDiscoverySource]:
    ids = _enabled_ids(registry, names=names)
    return [registry[provider_id] for provider_id in ids]


def enabled_content(
    registry: dict[str, BaseContentSource],
    *,
    names: list[str] | None = None,
) -> list[BaseContentSource]:
    ids = _enabled_ids(registry, names=names)
    return [registry[provider_id] for provider_id in ids]
