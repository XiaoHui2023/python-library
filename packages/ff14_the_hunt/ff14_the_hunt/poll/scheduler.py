from __future__ import annotations



import time

from collections.abc import Callable

from typing import Protocol



from ff14_the_hunt.models import HuntMarkRecord, HuntQueryFilter

from ff14_the_hunt.poll.monitor_mode import PollMonitorMode, resolve_poll_monitor_mode
from ff14_the_hunt.poll.sleep_plan import compute_poll_sleep_seconds
from ff14_the_hunt.poll.sleep_settings import PollSleepSettings
from ff14_the_hunt.poll.spawn_dedup import SpawnReportTracker





class HuntQuerySource(Protocol):

    """``HuntPollScheduler`` 所需的查询门面。"""



    def query_marks(

        self,

        query: HuntQueryFilter,

        *,

        include_spawn_states: bool = False,

        include_spawn_maps: bool = True,

        recent_grace_seconds: float = 900.0,

    ) -> list[HuntMarkRecord]: ...





class HuntPollScheduler:

    """狩猎计时轮询：按开窗状态在「睡到最近开窗」与短间隔轮询间切换。"""



    def __init__(

        self,

        hunt: HuntQuerySource,

        query: HuntQueryFilter,

        *,

        sleep_settings: PollSleepSettings | None = None,

        recent_grace_seconds: float = 900.0,

        include_spawn_states: bool = False,

        include_spawn_maps: bool = True,

        poll_interval_seconds: float | None = None,

        min_wakeup_seconds: float | None = None,

        active_poll_interval_seconds: float | None = None,

        recent_poll_interval_seconds: float | None = None,

        fallback_poll_interval_seconds: float | None = None,

    ) -> None:

        """绑定门面与筛选条件，并配置轮询节奏。



        Args:

            hunt: 狩猎数据门面。

            query: 每次爬取使用的筛选条件。

            sleep_settings: 轮询间隔与开窗唤醒下限；省略时用默认值。

            recent_grace_seconds: 传给查询的「刚刷新」宽限秒数。

            include_spawn_states: 已废弃；保留兼容。

            include_spawn_maps: 是否为刚刷新记录拉取区域原图。

            poll_interval_seconds: 已废弃；等同 ``fallback_poll_interval_seconds``。

            min_wakeup_seconds: 覆盖 ``sleep_settings.min_wakeup_seconds``。

            active_poll_interval_seconds: 覆盖活跃模式间隔。

            recent_poll_interval_seconds: 覆盖刚刷新模式间隔。

            fallback_poll_interval_seconds: 覆盖兜底间隔。

        """

        self._hunt = hunt

        self._query = query

        self._sleep_settings = self._resolve_sleep_settings(

            sleep_settings=sleep_settings,

            poll_interval_seconds=poll_interval_seconds,

            min_wakeup_seconds=min_wakeup_seconds,

            active_poll_interval_seconds=active_poll_interval_seconds,

            recent_poll_interval_seconds=recent_poll_interval_seconds,

            fallback_poll_interval_seconds=fallback_poll_interval_seconds,

        )

        self._recent_grace_seconds = recent_grace_seconds

        self._include_spawn_states = include_spawn_states

        self._include_spawn_maps = include_spawn_maps

        self._last_marks: list[HuntMarkRecord] = []
        self._last_crawl_at: float | None = None
        self._spawn_tracker = SpawnReportTracker()



    @staticmethod

    def _resolve_sleep_settings(

        *,

        sleep_settings: PollSleepSettings | None,

        poll_interval_seconds: float | None,

        min_wakeup_seconds: float | None,

        active_poll_interval_seconds: float | None,

        recent_poll_interval_seconds: float | None,

        fallback_poll_interval_seconds: float | None,

    ) -> PollSleepSettings:

        base = sleep_settings or PollSleepSettings()

        fallback = fallback_poll_interval_seconds

        if fallback is None and poll_interval_seconds is not None:

            fallback = poll_interval_seconds

        return PollSleepSettings(

            active_poll_interval_seconds=(

                active_poll_interval_seconds

                if active_poll_interval_seconds is not None

                else base.active_poll_interval_seconds

            ),

            recent_poll_interval_seconds=(

                recent_poll_interval_seconds

                if recent_poll_interval_seconds is not None

                else base.recent_poll_interval_seconds

            ),

            fallback_poll_interval_seconds=(

                fallback

                if fallback is not None

                else base.fallback_poll_interval_seconds

            ),

            min_wakeup_seconds=(

                min_wakeup_seconds

                if min_wakeup_seconds is not None

                else base.min_wakeup_seconds

            ),

        )



    @property

    def sleep_settings(self) -> PollSleepSettings:

        return self._sleep_settings



    @property

    def poll_interval_seconds(self) -> float:

        return self._sleep_settings.fallback_poll_interval_seconds



    @property

    def min_wakeup_seconds(self) -> float:

        return self._sleep_settings.min_wakeup_seconds



    @property

    def last_marks(self) -> list[HuntMarkRecord]:

        return list(self._last_marks)



    @property

    def last_crawl_at(self) -> float | None:

        return self._last_crawl_at



    def monitor_mode(self) -> PollMonitorMode | None:

        if self._last_crawl_at is None:

            return None

        return resolve_poll_monitor_mode(self._last_marks)



    def fetch(self) -> list[HuntMarkRecord]:

        marks = self._hunt.query_marks(
            self._query,
            include_spawn_states=self._include_spawn_states,
            include_spawn_maps=self._include_spawn_maps,
            recent_grace_seconds=self._recent_grace_seconds,
        )
        self._spawn_tracker.apply(marks)
        self._last_marks = marks

        self._last_crawl_at = time.time()

        return marks



    def seconds_until_next_fetch(self, *, now: float | None = None) -> float:

        if self._last_crawl_at is None:

            return 0.0

        return compute_poll_sleep_seconds(

            self._last_marks,

            settings=self._sleep_settings,

            last_crawl_at=self._last_crawl_at,

            now=now,

        )



    def run_forever(

        self,

        on_marks: Callable[[list[HuntMarkRecord]], None],

        *,

        should_stop: Callable[[], bool] | None = None,

        sleep: Callable[[float], None] | None = None,

    ) -> None:

        if sleep is None:

            sleep = time.sleep

        if should_stop is None:

            should_stop = lambda: False



        marks = self.fetch()

        on_marks(marks)



        while not should_stop():

            wait_seconds = self.seconds_until_next_fetch()

            if wait_seconds > 0:

                sleep(wait_seconds)

            if should_stop():

                break

            marks = self.fetch()

            on_marks(marks)

