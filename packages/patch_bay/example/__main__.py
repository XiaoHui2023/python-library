from __future__ import annotations

import asyncio
import logging

__all__ = ["demo", "main"]


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # 只关心本包与 aiohttp 测试服务器的噪声控制
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


async def demo() -> None:
    """在同一进程内用 aiohttp TestServer 拉起 PatchBay，两个 Jack 经路由互发一帧数据。

    实际部署时：PatchBay 通常单独进程 ``await PatchBay(config).serve()``，
    各业务进程 ``Jack(port, address=…)`` + ``await jack.start()``；``address`` 与 PatchBay 配置里该机条目一致（也可用环境变量 ``PATCH_BAY_ADDRESS``）。
    """
    from aiohttp.test_utils import TestServer

    from patch_bay import Jack, LoggingJackListener, LoggingPatchBayListener, PatchBay

    _configure_logging()

    cfg = {
        "listen": 0,
        "jacks": [
            {"name": "a", "address": "127.0.0.1:7001"},
            {"name": "b", "address": "127.0.0.1:7002"},
        ],
        "wires": [{"from": "a", "to": "b", "rule": "pass"}],
        "rules": {"pass": "True"},
    }
    pb = PatchBay(cfg, listeners=[LoggingPatchBayListener()])
    async with TestServer(pb.build_application()) as server:
        port = server.port
        loop = asyncio.get_running_loop()
        got: asyncio.Future[dict] = loop.create_future()

        jack_b = Jack(port, address="127.0.0.1:7002", listeners=[LoggingJackListener()])

        @jack_b
        async def _(payload: dict) -> None:
            if not got.done():
                got.set_result(payload)

        jack_a = Jack(port, address="127.0.0.1:7001", listeners=[LoggingJackListener()])
        await jack_a.start()
        await jack_b.start()
        await asyncio.sleep(0.2)
        await jack_a.send({"msg": "hello from demo"})
        data = await asyncio.wait_for(got, timeout=3.0)
        await jack_a.aclose()
        await jack_b.aclose()
    print("patch_bay demo ok:", data)


def main() -> None:
    asyncio.run(demo())


if __name__ == "__main__":
    main()
