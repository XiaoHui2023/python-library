from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from hotmeme.config_build import build_config
from hotmeme.crawl.delta import dedupe_images_by_id, partition_new_images
from hotmeme.crawl.packet import HotMemeCrawlPacket
from hotmeme.crawl.round import FetchedRound
from hotmeme.assets import materialize_image_items_traced
from hotmeme.models import (
    AssetsPolicy,
    HotMemeModels,
    HotPostsQuery,
    ImageFeed,
    ImageItem,
    PipelinePolicy,
    XiaohongshuPolicy,
)
from hotmeme.pipeline.fetch_hot_posts import fetch_hot_posts
from hotmeme.renderer import MemeOutputBatch, render_items
from hotmeme.sources.tikhub import TikHubSource


class HotMeme:
    """热帖聚合：TikHub 拉帖、带增量记忆的单次爬取。"""

    def __init__(
        self,
        *,
        config_path: Path | str | None = None,
        tikhub_enabled: bool = True,
        api_key: str | None = None,
        source_timeout: float = 5.0,
        allow_nsfw: bool = False,
        platforms: list[str] | None = None,
        per_source_timeout: float = 5.0,
        retries: int = 1,
        skip_failed_providers: bool = True,
        xiaohongshu: XiaohongshuPolicy | None = None,
        xhs_page: int | None = None,
        xhs_sort_type: str | None = None,
        xhs_time_filter: str | None = None,
        xhs_search_tags: list[str] | None = None,
        xhs_min_score: float | None = None,
    ) -> None:
        """构造聚合器。

        Args:
            config_path: YAML/JSON 配置文件；指定时忽略其余构造项。
            tikhub_enabled: 是否启用 TikHub。
            api_key: TikHub API key。
            source_timeout: TikHub 请求超时秒数。
            allow_nsfw: 是否允许 NSFW 内容。
            platforms: 拉帖平台列表；默认仅小红书。
            per_source_timeout: 单平台聚合超时秒数。
            retries: 失败重试次数。
            skip_failed_providers: 单平台失败时是否跳过并继续。
            xiaohongshu: 小红书策略整块覆盖。
            xhs_page: 小红书搜索页码。
            xhs_sort_type: 小红书排序，默认综合。
            xhs_time_filter: 小红书发布时间筛选。
            xhs_search_tags: 小红书话题 tag 列表。
            xhs_min_score: 小红书最低互动分（须大于该值）。
        """
        self._config = build_config(
            config_path=config_path,
            tikhub_enabled=tikhub_enabled,
            api_key=api_key,
            source_timeout=source_timeout,
            allow_nsfw=allow_nsfw,
            platforms=platforms,
            per_source_timeout=per_source_timeout,
            retries=retries,
            skip_failed_providers=skip_failed_providers,
            xiaohongshu=xiaohongshu,
            xhs_page=xhs_page,
            xhs_sort_type=xhs_sort_type,
            xhs_time_filter=xhs_time_filter,
            xhs_search_tags=xhs_search_tags,
            xhs_min_score=xhs_min_score,
        )
        self._seen_item_ids: set[str] = set()
        self._has_crawled = False

    @property
    def config(self) -> HotMemeModels:
        return self._config

    def _pipeline(self) -> PipelinePolicy:
        return self._config.pipeline or PipelinePolicy()

    @property
    def platforms(self) -> list[str]:
        return list(self._pipeline().platforms)

    @property
    def tikhub(self) -> TikHubSource | None:
        section = self._config.tikhub
        if section is None:
            return None
        return TikHubSource(section)

    def reset_seen(self) -> None:
        """清空已见 ID，下次 ``crawl_once`` 将全部视为新增。"""
        self._seen_item_ids.clear()
        self._has_crawled = False

    def crawl_once(self) -> HotMemeCrawlPacket:
        """拉取热帖一次，并返回相对上次新增的数据包。"""
        round_result = self._fetch_round()
        fetched_items = dedupe_images_by_id(round_result.items)
        is_initial = not self._has_crawled
        new_items = partition_new_images(fetched_items, self._seen_item_ids)
        self._has_crawled = True
        return HotMemeCrawlPacket(
            crawled_at=datetime.now(UTC),
            new_items=new_items,
            fetched_items=fetched_items,
            providers_ok=round_result.providers_ok,
            providers_failed=round_result.providers_failed,
            fetch_errors=round_result.fetch_errors,
            api_calls=round_result.api_calls,
            is_initial=is_initial,
            diagnostics=round_result.diagnostics,
        )

    def fetch_hot_posts(
        self,
        *,
        platforms: list[str] | None = None,
        allow_nsfw: bool | None = None,
    ) -> ImageFeed:
        """按平台拉热帖并质检。"""
        query = HotPostsQuery(
            platforms=platforms,
            allow_nsfw=allow_nsfw,
        )
        return fetch_hot_posts(
            self._config.tikhub,
            self._pipeline(),
            self._config.fetch,
            query,
            xiaohongshu=self._config.xiaohongshu,
        )

    def render_output(
        self,
        items: list[ImageItem],
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> MemeOutputBatch:
        """筛选后的热帖项下载图片并渲染为可交付输出包。"""
        assets = self._config.assets or AssetsPolicy()
        prepared, errors, stage = materialize_image_items_traced(
            items,
            policy=assets,
            on_progress=on_progress,
        )
        if on_progress is not None:
            on_progress(f"渲染输出包 {len(prepared)} 条…")
        batch = render_items(
            prepared,
            max_images_per_item=assets.max_images_per_item,
        )
        return batch.model_copy(
            update={
                "materialize_errors": errors,
                "materialize_stage": stage,
            },
        )

    def render_crawl_packet(self, packet: HotMemeCrawlPacket) -> MemeOutputBatch:
        """渲染爬取数据包中的新增热帖。"""
        return self.render_output(packet.new_items)

    def crawl_and_render(self) -> tuple[HotMemeCrawlPacket, MemeOutputBatch]:
        """爬取一次并渲染新增热帖为输出包。"""
        packet = self.crawl_once()
        return packet, self.render_crawl_packet(packet)

    def _fetch_round(self) -> FetchedRound:
        feed = self.fetch_hot_posts()
        return FetchedRound(
            items=list(feed.items),
            providers_ok=list(feed.providers_ok),
            providers_failed=list(feed.providers_failed),
            fetch_errors=list(feed.fetch_errors),
            api_calls=list(feed.api_calls),
            diagnostics=feed.diagnostics,
        )
