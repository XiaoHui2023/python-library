from __future__ import annotations

import threading
import time
from collections.abc import Callable

from ff14_the_hunt.bear_tracker.client import BearTrackerClient
from ff14_the_hunt.bear_tracker.enrich import build_hunt_record, mark_has_display_timer
from ff14_the_hunt.bear_tracker.resources import BearResources
from ff14_the_hunt.locale.cn import normalize_patch_codes
from ff14_the_hunt.models import (
    HuntCrawlPacket,
    HuntMarkRecord,
    HuntQueryFilter,
    HuntRankKind,
)
from ff14_the_hunt.poll.loop import wait_or_stop
from ff14_the_hunt.poll.scheduler import HuntPollScheduler
from ff14_the_hunt.spawn_map.attach import enrich_recent_spawn_details
from ff14_the_hunt.spawn_map.region_fetch import RegionMapFetcher, site_root_from_api_base

HuntCrawlCallback = Callable[[HuntCrawlPacket], None]


class FF14TheHunt:
    """FF14 狩猎追踪门面：当前对接 [Bear Tracker](https://tracker.beartoolkit.com/timer)。"""

    def __init__(
        self,
        *,
        data_centers: list[str] | None = None,
        worlds: list[str] | None = None,
        rank_kinds: list[HuntRankKind] | None = None,
        patches: list[str] | None = None,
        hunt_keys: list[str] | None = None,
        regions: list[str] | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 120.0,
        active_poll_interval_seconds: float = 600.0,
        recent_poll_interval_seconds: float = 300.0,
        fallback_poll_interval_seconds: float = 1800.0,
        min_wakeup_seconds: float = 120.0,
        recent_grace_seconds: float = 900.0,
        poll_interval_seconds: float | None = None,
        include_spawn_states: bool = False,
        include_spawn_maps: bool = True,
        include_untimed_marks: bool = False,
    ) -> None:
        """绑定服务器筛选与轮询节奏，构造后即可手动或自动爬取。

        Args:
            data_centers: 数据中心名；中国区如猫小胖、莫古力。
            worlds: 世界名；为空时由 data_centers 展开全部世界。
            rank_kinds: A / S / FATE；默认仅 S。
            patches: 资料片，如 DT 或金曦之遗辉；空表示不过滤。
            hunt_keys: 限定 huntKey；空表示不过滤。
            regions: 地图区域名；空表示不过滤。
            base_url: Bear Tracker 根地址；默认官方站点。
            timeout_seconds: HTTP 超时秒数。
            active_poll_interval_seconds: 开窗中/强制期等活跃模式轮询间隔（秒），默认 10 分钟。
            recent_poll_interval_seconds: 存在刚刷新条目时的轮询间隔（秒），默认 5 分钟。
            fallback_poll_interval_seconds: 无触发计时时轮询间隔（秒），默认 30 分钟。
            min_wakeup_seconds: 全未开窗时睡到最近开窗的下限（秒），默认 2 分钟。
            poll_interval_seconds: 已废弃；等同 ``fallback_poll_interval_seconds``。
            recent_grace_seconds: 「刚刷新」宽限秒数。
            include_spawn_states: 已废弃；刚刷新记录的存活点会在补全刷点时自动查询。
            include_spawn_maps: 为刚刷新记录拉取站点区域原图 PNG base64。
            include_untimed_marks: 是否保留无计时的占位行（SS 级噬灵王、维护占位等）。
        """
        kwargs: dict[str, float | str] = {"timeout_seconds": timeout_seconds}
        if base_url is not None:
            kwargs["base_url"] = base_url
        self._client = BearTrackerClient(**kwargs)
        self._resources: BearResources | None = None
        self._query = HuntQueryFilter(
            data_centers=list(data_centers or []),
            worlds=list(worlds or []),
            rank_kinds=list(rank_kinds or [HuntRankKind.S]),
            patches=normalize_patch_codes(list(patches or [])),
            hunt_keys=list(hunt_keys or []),
            regions=list(regions or []),
            include_untimed_marks=include_untimed_marks,
        )
        self._recent_grace_seconds = recent_grace_seconds
        self._include_spawn_states = include_spawn_states
        self._include_spawn_maps = include_spawn_maps
        self._map_fetcher: RegionMapFetcher | None = None
        self._scheduler = HuntPollScheduler(
            self,
            self._query,
            poll_interval_seconds=poll_interval_seconds,
            active_poll_interval_seconds=active_poll_interval_seconds,
            recent_poll_interval_seconds=recent_poll_interval_seconds,
            fallback_poll_interval_seconds=fallback_poll_interval_seconds,
            min_wakeup_seconds=min_wakeup_seconds,
            recent_grace_seconds=recent_grace_seconds,
            include_spawn_states=include_spawn_states,
            include_spawn_maps=include_spawn_maps,
        )
        self._callbacks: list[HuntCrawlCallback] = []
        self._service_lock = threading.Lock()
        self._stop_event: threading.Event | None = None
        self._poll_thread: threading.Thread | None = None

    @property
    def query(self) -> HuntQueryFilter:
        return self._query

    @property
    def client(self) -> BearTrackerClient:
        return self._client

    @property
    def scheduler(self) -> HuntPollScheduler:
        return self._scheduler

    @property
    def is_running(self) -> bool:
        thread = self._poll_thread
        return thread is not None and thread.is_alive()

    def ensure_resources(self) -> BearResources:
        if self._resources is None:
            session = self._client.sync_session()
            raw = session.get("resources", {})
            self._resources = BearResources(raw)
        return self._resources

    def list_data_centers(self, *, region: str | None = None) -> list[str]:
        """列出数据中心名；``region='CN'`` 仅中国区。"""
        resources = self.ensure_resources()
        names: list[str] = []
        for name, info in resources.data_centers.items():
            if region is not None and info.get("Region") != region:
                continue
            names.append(name)
        return sorted(names)

    def list_worlds(self, data_centers: list[str]) -> list[str]:
        resources = self.ensure_resources()
        return resources.worlds_for_data_centers(data_centers)

    def on_crawl(
        self,
        callback: HuntCrawlCallback | None = None,
    ) -> HuntCrawlCallback | Callable[[HuntCrawlCallback], HuntCrawlCallback]:
        """登记单次爬取回调；省略参数时可用作装饰器。

        Args:
            callback: 接收 ``HuntCrawlPacket`` 的处理函数。

        Returns:
            装饰器模式下返回原函数；直接传入时返回同一回调。
        """
        if callback is not None:
            self._callbacks.append(callback)
            return callback

        def decorator(fn: HuntCrawlCallback) -> HuntCrawlCallback:
            self._callbacks.append(fn)
            return fn

        return decorator

    def __call__(self, callback: HuntCrawlCallback) -> HuntCrawlCallback:
        return self.on_crawl(callback)

    def crawl_once(self) -> HuntCrawlPacket:
        """手动执行一次爬取，并触发已登记回调。"""
        marks = self._scheduler.fetch()
        packet = self._make_crawl_packet(marks)
        self._emit_crawl(packet)
        return packet

    def start(self) -> None:
        """在后台线程启动自动轮询，不阻塞当前线程。"""
        with self._service_lock:
            if self.is_running:
                return
            self._stop_event = threading.Event()
            self._poll_thread = threading.Thread(
                target=self._poll_loop,
                name="ff14-the-hunt-poll",
                daemon=True,
            )
            self._poll_thread.start()

    def stop(self, *, join: bool = True, timeout: float | None = None) -> None:
        """停止自动轮询；与 ``start`` / ``run`` 配对。"""
        with self._service_lock:
            if self._stop_event is not None:
                self._stop_event.set()
            thread = self._poll_thread
            if join and thread is not None and thread.is_alive():
                if thread is threading.current_thread():
                    return
                thread.join(timeout=timeout)
            if join:
                self._poll_thread = None

    def run(self) -> None:
        """在当前线程阻塞运行自动轮询，直至 ``stop`` 或 Ctrl+C。"""
        with self._service_lock:
            if self.is_running:
                raise RuntimeError("poll service already running; call stop() first")
            self._stop_event = threading.Event()
        try:
            self._poll_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop(join=False)
            with self._service_lock:
                self._poll_thread = None
                self._stop_event = None

    def query_marks(
        self,
        query: HuntQueryFilter | None = None,
        *,
        include_spawn_states: bool | None = None,
        include_spawn_maps: bool | None = None,
        recent_grace_seconds: float | None = None,
    ) -> list[HuntMarkRecord]:
        """按筛选条件查询并解析狩猎计时。

        Args:
            query: 筛选条件；省略时用构造时的配置。
            include_spawn_states: 已废弃；保留参数兼容。
            include_spawn_maps: 为刚刷新记录拉取区域原图；省略时用构造配置。
            recent_grace_seconds: 开窗或标记后多少秒内视为「刚刷新」。
        """
        active_query = self._query if query is None else query
        del include_spawn_states
        attach_maps = (
            self._include_spawn_maps
            if include_spawn_maps is None
            else include_spawn_maps
        )
        grace = (
            self._recent_grace_seconds
            if recent_grace_seconds is None
            else recent_grace_seconds
        )
        resources = self.ensure_resources()
        worlds = list(active_query.worlds)
        if not worlds:
            worlds = resources.worlds_for_data_centers(active_query.data_centers)
        if not worlds:
            return []

        rows: list[dict] = []
        for rank in active_query.rank_kinds:
            rows.extend(
                self._client.last_death_timers(
                    world_names=worlds,
                    rank_type=rank.value,
                )
            )

        records: list[HuntMarkRecord] = []
        kept_rows: list[dict] = []
        for row in rows:
            record = build_hunt_record(
                timer_row=row,
                resources=resources,
                query=active_query,
                recent_grace_seconds=grace,
            )
            if record is None:
                continue
            if active_query.include_untimed_marks or mark_has_display_timer(record):
                records.append(record)
                kept_rows.append(row)
        enrich_recent_spawn_details(
            records,
            kept_rows,
            resources=resources,
            fetcher=self._region_map_fetcher() if attach_maps else None,
            load_spawn_states=self._load_spawn_states,
            include_region_map=attach_maps,
        )
        return records

    def _region_map_fetcher(self) -> RegionMapFetcher:
        if self._map_fetcher is None:
            self._map_fetcher = RegionMapFetcher(
                site_root=site_root_from_api_base(self._client.base_url),
                timeout_seconds=self._client.timeout_seconds,
            )
        return self._map_fetcher

    def recently_spawned(
        self,
        query: HuntQueryFilter | None = None,
        *,
        recent_grace_seconds: float | None = None,
    ) -> list[HuntMarkRecord]:
        marks = self.query_marks(
            query,
            recent_grace_seconds=recent_grace_seconds,
        )
        return [mark for mark in marks if mark.recently_spawned]

    def newly_spawned(
        self,
        query: HuntQueryFilter | None = None,
        *,
        recent_grace_seconds: float | None = None,
    ) -> list[HuntMarkRecord]:
        """返回经轮询去重后、本会话尚未上报过的刚刷新记录。"""
        del query, recent_grace_seconds
        return [mark for mark in self._scheduler.last_marks if mark.newly_spawned]

    def _poll_loop(self) -> None:
        stop_event = self._stop_event
        if stop_event is None:
            return

        marks = self._scheduler.fetch()
        self._emit_crawl(self._make_crawl_packet(marks))

        while not stop_event.is_set():
            wait_seconds = self._scheduler.seconds_until_next_fetch()
            if wait_seconds > 0 and wait_or_stop(stop_event, wait_seconds):
                break
            if stop_event.is_set():
                break
            marks = self._scheduler.fetch()
            self._emit_crawl(self._make_crawl_packet(marks))

    def _make_crawl_packet(self, marks: list[HuntMarkRecord]) -> HuntCrawlPacket:
        crawled_at = self._scheduler.last_crawl_at
        if crawled_at is None:
            crawled_at = time.time()
        return HuntCrawlPacket(
            crawled_at=crawled_at,
            marks=marks,
            query=self._query,
        )

    def _emit_crawl(self, packet: HuntCrawlPacket) -> None:
        for callback in self._callbacks:
            callback(packet)

    def _load_spawn_states(
        self,
        row: dict,
        resources: BearResources,
    ) -> dict | None:
        hunt_key = str(row.get("huntKey") or "")
        world_name = str(row.get("worldName") or "")
        if not hunt_key or not world_name:
            return None
        meta = resources.hunt_meta(hunt_key)
        last_death = row.get("lastMarkTime") or row.get("lastDeathTime")
        try:
            states = self._client.query_spawn_points(
                hunt_name=hunt_key,
                world_name=world_name,
                last_death=float(last_death) if last_death else None,
            )
        except RuntimeError:
            return None
        return states if isinstance(states, dict) else None
