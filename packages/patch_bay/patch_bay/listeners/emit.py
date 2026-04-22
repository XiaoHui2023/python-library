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
    """调用每个 listener 上名为 ``method`` 的可调用（若存在且可调用）。"""
    for lst in listeners:
        fn = getattr(lst, method, None)
        if not callable(fn):
            continue
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("listener %s.%s failed", type(lst).__name__, method)
