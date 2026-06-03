from __future__ import annotations

import time
from datetime import datetime


class ExamplePrintTiming:
    """示例终端打印用计时：``tag()`` 为本地时分秒前缀；``reset()`` 起算轮次总耗时。"""

    def __init__(self) -> None:
        self._t0: float | None = None

    def reset(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed_s(self) -> float:
        if self._t0 is None:
            self.reset()
            return 0.0
        return time.perf_counter() - self._t0

    def tag(self) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}]"