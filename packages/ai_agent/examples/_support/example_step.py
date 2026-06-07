from __future__ import annotations

import sys
from datetime import datetime


def example_step(msg: str) -> None:
    """向 stderr 打印带毫秒时间戳的步骤说明（示例流水线用）。"""
    now = datetime.now()
    ms = now.microsecond // 1000
    ts = now.strftime("%Y-%m-%d %H:%M:%S") + f".{ms:03d}"
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)
