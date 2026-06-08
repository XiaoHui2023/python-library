from __future__ import annotations

from pathlib import Path

from hotmeme.config_load import load_config
from hotmeme.models import (
    DEFAULT_PLATFORMS,
    FetchPolicy,
    HotMemeModels,
    PipelinePolicy,
    TikHubConfig,
    XiaohongshuPolicy,
)


def build_config(
    *,
    config_path: Path | str | None = None,
    tikhub_enabled: bool = True,
    api_key: str | None = None,
    base_url: str = "https://api.tikhub.io",
    source_timeout: float = 5.0,
    allow_nsfw: bool = False,
    platforms: list[str] | None = None,
    per_source_timeout: float = 5.0,
    retries: int = 1,
    skip_failed_providers: bool = True,
    xiaohongshu: XiaohongshuPolicy | None = None,
    xhs_tags_enabled: bool | None = None,
    xhs_page: int | None = None,
    xhs_sort_type: str | None = None,
    xhs_time_filter: str | None = None,
    xhs_search_tags: list[str] | None = None,
    xhs_min_score: float | None = None,
) -> HotMemeModels:
    """由平铺入参或配置文件组装根配置。"""
    xhs_overrides: dict[str, object] = {}
    if xhs_tags_enabled is not None:
        xhs_overrides["tags_enabled"] = xhs_tags_enabled
    if xhs_page is not None:
        xhs_overrides["page"] = xhs_page
    if xhs_sort_type is not None:
        xhs_overrides["sort_type"] = xhs_sort_type
    if xhs_time_filter is not None:
        xhs_overrides["time_filter"] = xhs_time_filter
    if xhs_search_tags is not None:
        xhs_overrides["search_tags"] = xhs_search_tags
    if xhs_min_score is not None:
        xhs_overrides["min_score"] = xhs_min_score

    if config_path is not None:
        models = load_config(config_path)
        updates: dict[str, object] = {}
        if api_key is not None and models.tikhub is not None:
            updates["tikhub"] = models.tikhub.model_copy(update={"api_key": api_key})
        if platforms is not None:
            pipeline = models.pipeline or PipelinePolicy()
            updates["pipeline"] = pipeline.model_copy(update={"platforms": platforms})
        if xiaohongshu is not None:
            updates["xiaohongshu"] = xiaohongshu
        elif xhs_overrides:
            base_xhs = models.xiaohongshu or XiaohongshuPolicy()
            updates["xiaohongshu"] = base_xhs.model_copy(update=xhs_overrides)
        if updates:
            models = models.model_copy(update=updates)
        return models
    pipeline = PipelinePolicy(
        platforms=platforms or [p.value for p in DEFAULT_PLATFORMS],
    )
    tikhub: TikHubConfig | None = None
    if tikhub_enabled:
        tikhub = TikHubConfig(
            enabled=True,
            api_key=api_key,
            base_url=base_url,
            timeout=source_timeout,
            allow_nsfw=allow_nsfw,
        )
    xhs_policy = xiaohongshu
    if xhs_policy is None:
        xhs_policy = XiaohongshuPolicy(**xhs_overrides) if xhs_overrides else None

    return HotMemeModels(
        tikhub=tikhub,
        pipeline=pipeline,
        xiaohongshu=xhs_policy,
        fetch=FetchPolicy(
            per_source_timeout=per_source_timeout,
            retries=retries,
            skip_failed_providers=skip_failed_providers,
        ),
    )
