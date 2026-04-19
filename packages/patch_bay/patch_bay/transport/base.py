from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Transport(Protocol):
    """可选的传输抽象：默认实现为 aiohttp WebSocket。"""

    async def send_bytes(self, data: bytes) -> None:
        ...

    async def close(self) -> None:
        ...
