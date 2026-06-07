from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from hotmeme.cn_models import (
    CnHotQuery,
    CnPipelinePolicy,
    CnSourcesConfig,
    DiscoverTopicsQuery,
    TopicFeed,
    default_cn_pipeline,
    default_cn_sources,
)
from hotmeme.config_load import load_config
from hotmeme.crawl.delta import (
    dedupe_images_by_id,
    partition_new_images,
    partition_new_topics,
)
from hotmeme.crawl.packet import HotMemeCrawlPacket
from hotmeme.crawl.round import FetchedRound
from hotmeme.models import FetchPolicy, HotMemeModels, ImageFeed
from hotmeme.sources.cn.discovery.hotpush import HotpushSource
from hotmeme.sources.cn.discovery_aggregate import aggregate_discover
from hotmeme.sources.cn.pipeline import fetch_cn_hot
from hotmeme.sources.cn.content.tikhub import TikHubSource
from hotmeme.sources.cn.registry import (
    build_cn_content,
    build_cn_discovery,
    enabled_content,
    enabled_discovery,
)


class HotMeme:
    """社会热点与梗图聚合：可配置多源、带增量记忆的单次爬取。"""

    def __init__(
        self,
        *,
        config: HotMemeModels | None = None,
        config_path: Path | str | None = None,
        cn: CnSourcesConfig | None = None,
        cn_pipeline: CnPipelinePolicy | None = None,
        fetch: FetchPolicy | None = None,
    ) -> None:
        """构造聚合器；仅注册配置里出现的来源。

        Args:
            config: 完整根配置；与 ``config_path``、分项参数互斥时优先。
            config_path: YAML/JSON 配置文件路径。
            cn: 热点源配置。
            cn_pipeline: 发现→搜图管线策略。
            fetch: 多源并发与条数上限。
        """
        if config is not None and config_path is not None:
            raise ValueError("config 与 config_path 只能指定其一")
        if config_path is not None:
            config = load_config(config_path)
        if config is None:
            config = HotMemeModels(
                cn=cn if cn is not None else default_cn_sources(),
                cn_pipeline=cn_pipeline or default_cn_pipeline(),
                fetch=fetch or FetchPolicy(),
            )
        self._config = config
        self._cn_discovery = (
            build_cn_discovery(self._config.cn)
            if self._config.cn is not None
            else {}
        )
        self._cn_content = (
            build_cn_content(self._config.cn)
            if self._config.cn is not None
            else {}
        )
        self._seen_image_ids: set[str] = set()
        self._seen_topic_ids: set[str] = set()
        self._has_crawled = False

    @property
    def config(self) -> HotMemeModels:
        return self._config

    def _require_cn(self) -> CnSourcesConfig:
        if self._config.cn is None:
            raise ValueError("未配置 cn 源；请在配置中启用热点源")
        return self._config.cn

    def _cn_pipeline(self) -> CnPipelinePolicy:
        return self._config.cn_pipeline or CnPipelinePolicy()

    @property
    def hotpush(self) -> HotpushSource | None:
        source = self._cn_discovery.get("hotpush")
        return source if isinstance(source, HotpushSource) else None

    @property
    def tikhub(self) -> TikHubSource | None:
        source = self._cn_content.get("tikhub")
        return source if isinstance(source, TikHubSource) else None

    def reset_seen(self) -> None:
        """清空已见 ID，下次 ``crawl_once`` 将全部视为新增。"""
        self._seen_image_ids.clear()
        self._seen_topic_ids.clear()
        self._has_crawled = False

    def crawl_once(self) -> HotMemeCrawlPacket:
        """拉取所有已启用源一次，并返回相对上次新增的数据包。"""
        round_result = self._fetch_round()
        fetched_items = dedupe_images_by_id(round_result.items)
        is_initial = not self._has_crawled
        new_items = partition_new_images(fetched_items, self._seen_image_ids)
        new_topics = partition_new_topics(round_result.topics, self._seen_topic_ids)
        self._has_crawled = True
        return HotMemeCrawlPacket(
            crawled_at=datetime.now(UTC),
            new_items=new_items,
            new_topics=new_topics,
            fetched_items=fetched_items,
            fetched_topics=list(round_result.topics),
            providers_ok=round_result.providers_ok,
            providers_failed=round_result.providers_failed,
            is_initial=is_initial,
        )

    def discover_topics(
        self,
        query: DiscoverTopicsQuery | None = None,
        /,
        **kwargs: object,
    ) -> TopicFeed:
        """各发现源独立拉榜后合并。"""
        self._require_cn()
        if query is None:
            query = DiscoverTopicsQuery.model_validate(kwargs)
        elif kwargs:
            raise ValueError("位置参数 query 与关键字参数不可同时使用")
        pipeline = self._cn_pipeline()
        return aggregate_discover(
            self._cn_discovery,
            query=query,
            classify=pipeline.classify_topics,
        )

    def fetch_cn_hot(
        self,
        query: CnHotQuery | None = None,
        /,
        **kwargs: object,
    ) -> ImageFeed:
        """发现 → 按热词搜图 → 合并。"""
        if query is None:
            query = CnHotQuery.model_validate(kwargs)
        elif kwargs:
            raise ValueError("位置参数 query 与关键字参数不可同时使用")
        self._require_cn()
        return fetch_cn_hot(
            self._config.cn,  # type: ignore[arg-type]
            self._cn_pipeline(),
            self._config.fetch,
            query,
        )

    def _fetch_round(self) -> FetchedRound:
        round_result = FetchedRound()
        if self._config.cn is None:
            return round_result
        if enabled_discovery(self._cn_discovery):
            topic_feed = self.discover_topics()
            round_result.topics.extend(topic_feed.topics)
            round_result.providers_ok.extend(topic_feed.providers_ok)
            round_result.providers_failed.extend(topic_feed.providers_failed)
        if enabled_content(self._cn_content) or enabled_discovery(self._cn_discovery):
            feed = self.fetch_cn_hot()
            round_result.items.extend(feed.items)
            round_result.providers_ok.extend(feed.providers_ok)
            round_result.providers_failed.extend(feed.providers_failed)
        round_result.providers_ok = list(dict.fromkeys(round_result.providers_ok))
        round_result.providers_failed = list(
            dict.fromkeys(round_result.providers_failed),
        )
        return round_result
