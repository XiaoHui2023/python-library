from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Transport(Protocol):
    """可替换的字节传输接口。"""

    async def send_bytes(self, data: bytes) -> None:
        ...

    async def close(self) -> None:
        ...
