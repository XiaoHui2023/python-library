from __future__ import annotations

import logging
from typing import Any

from .patch_bay_listener import PatchBayListener

logger = logging.getLogger(__name__)


def emit_listeners(
    listeners: list[PatchBayListener],
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """向所有监听器广播一个运行事件。

    Args:
        listeners: 已注册的监听器列表。
        method: 要调用的监听器方法名。
        *args: 传给监听器方法的位置参数。
        **kwargs: 传给监听器方法的关键字参数。

    Returns:
        None: 监听器异常会被记录，不会中断后续监听器。
    """
    for lst in listeners:
        fn = getattr(lst, method, None)
        if not callable(fn):
            continue
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("listener %s.%s failed", type(lst).__name__, method)
