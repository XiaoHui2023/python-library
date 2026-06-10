import threading
import time
import urllib.error
from unittest.mock import MagicMock, patch

from ff14_the_hunt import FF14TheHunt, HuntCrawlPacket, HuntQueryFilter, HuntRankKind
from ff14_the_hunt.bear_tracker.timer_theme import build_timer_display
from ff14_the_hunt.models import (
    HuntMarkRecord,
    SpawnWindowPhase,
    TimerBarColor,
    TimerKind,
)
from ff14_the_hunt.poll.loop import wait_or_stop


def _sample_mark() -> HuntMarkRecord:
    return HuntMarkRecord(
        hunt_key="k",
        hunt_name="n",
        world_name="w",
        trigger_timer=build_timer_display(
            kind=TimerKind.TRIGGER,
            phase=SpawnWindowPhase.ALMOST_OPEN,
            bar_color=TimerBarColor.ERROR,
            counts_up=False,
            remaining_seconds=900.0,
            summary="test",
        ),
    )


def _hunt_with_mock_query() -> tuple[FF14TheHunt, MagicMock]:
    hunt = FF14TheHunt(
        rank_kinds=[HuntRankKind.S],
        fallback_poll_interval_seconds=60.0,
        active_poll_interval_seconds=60.0,
        min_wakeup_seconds=10.0,
    )
    mock_query = MagicMock(return_value=[_sample_mark()])
    hunt.query_marks = mock_query  # type: ignore[method-assign]
    return hunt, mock_query


def test_on_crawl_decorator() -> None:
    hunt, _ = _hunt_with_mock_query()
    seen: list[HuntCrawlPacket] = []

    @hunt.on_crawl
    def handle(packet: HuntCrawlPacket) -> None:
        seen.append(packet)

    hunt.crawl_once()
    assert len(seen) == 1
    assert seen[0].marks[0].hunt_key == "k"


def test_callable_decorator() -> None:
    hunt, _ = _hunt_with_mock_query()
    seen: list[HuntCrawlPacket] = []

    @hunt
    def handle(packet: HuntCrawlPacket) -> None:
        seen.append(packet)

    hunt.crawl_once()
    assert len(seen) == 1


def test_crawl_once_returns_packet() -> None:
    hunt, mock_query = _hunt_with_mock_query()
    packet = hunt.crawl_once()
    assert mock_query.call_count == 1
    assert isinstance(packet, HuntCrawlPacket)
    assert packet.query is hunt.query
    assert len(packet.marks) == 1
    assert packet.next_fetch_at >= packet.crawled_at


def test_start_stop_poll_service() -> None:
    hunt, mock_query = _hunt_with_mock_query()
    seen: list[HuntCrawlPacket] = []
    hunt.on_crawl(lambda packet: seen.append(packet))

    hunt.start()
    deadline = time.time() + 5.0
    while time.time() < deadline and len(seen) < 1:
        time.sleep(0.05)
    hunt.stop()
    assert len(seen) >= 1
    assert mock_query.call_count >= 1


def test_run_stop_from_other_thread() -> None:
    hunt, mock_query = _hunt_with_mock_query()
    hunt.on_crawl(lambda _packet: None)

    thread = threading.Thread(target=hunt.run)
    thread.start()
    time.sleep(0.2)
    hunt.stop()
    thread.join(timeout=3.0)
    assert not thread.is_alive()
    assert mock_query.call_count >= 1


def test_wait_or_stop() -> None:
    stop_event = threading.Event()
    assert wait_or_stop(stop_event, 0.1) is False
    stop_event.set()
    assert wait_or_stop(stop_event, 1.0) is True


def test_poll_loop_survives_callback_failure() -> None:
    hunt, _mock_query = _hunt_with_mock_query()
    hunt.on_crawl(lambda _packet: (_ for _ in ()).throw(RuntimeError("sink")))
    stop_event = threading.Event()
    hunt._poll_once_or_wait(stop_event)  # type: ignore[attr-defined]


def test_poll_loop_survives_fetch_failure() -> None:
    hunt, mock_query = _hunt_with_mock_query()
    seen: list[HuntCrawlPacket] = []
    hunt.on_crawl(lambda packet: seen.append(packet))
    mock_query.side_effect = [
        urllib.error.URLError("transient"),
        [_sample_mark()],
    ]

    stop_event = threading.Event()
    with patch("ff14_the_hunt.ff14_the_hunt.wait_or_stop", return_value=False):
        hunt._poll_once_or_wait(stop_event)  # type: ignore[attr-defined]
        hunt._poll_once_or_wait(stop_event)  # type: ignore[attr-defined]

    assert mock_query.call_count == 2
    assert len(seen) == 1


def test_wait_or_stop_wakes_early_on_stop() -> None:
    stop_event = threading.Event()

    def _set_stop() -> None:
        time.sleep(0.05)
        stop_event.set()

    threading.Thread(target=_set_stop, daemon=True).start()
    started = time.monotonic()
    assert wait_or_stop(stop_event, 30.0) is True
    assert time.monotonic() - started < 2.0
