from __future__ import annotations

import logging
from typing import Any

from .jack_listener import JackListener

logger = logging.getLogger(__name__)


def emit_jack_listeners(
    listeners: list[JackListener],
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """按名称在监听器列表上分发同步回调；单监听器异常不影响其余项。

    Args:
        listeners: 已注册的监听器实例列表。
        method: 要调用的回调方法名（存在且可调用才执行）。
        *args: 透传给该方法的定位参数。
        **kwargs: 透传给该方法的关键字参数。

    Returns:
        无。
    """
    for lst in listeners:
        fn = getattr(lst, method, None)
        if not callable(fn):
            continue
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("jack listener %s.%s failed", type(lst).__name__, method)
