from __future__ import annotations

import threading
import time

_WAIT_SLICE_SECONDS = 1.0


def wait_or_stop(stop_event: threading.Event, seconds: float) -> bool:
    """等待指定秒数，或在 stop 事件触发时提前结束。

    Args:
        stop_event: 置位时表示应停止轮询。
        seconds: 最长等待秒数。

    Returns:
        ``True`` 表示 stop 已触发；``False`` 表示正常等满。
    """
    if seconds <= 0:
        return stop_event.is_set()
    deadline = time.monotonic() + seconds
    while not stop_event.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        slice_seconds = min(remaining, _WAIT_SLICE_SECONDS)
        if stop_event.wait(timeout=slice_seconds):
            return True
    return True
