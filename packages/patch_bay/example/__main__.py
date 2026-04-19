from __future__ import annotations

import asyncio

__all__ = ["demo", "main"]


async def demo() -> None:
    """在同一进程内用 aiohttp TestServer 拉起 PatchBay，两个 Jack 经路由互发一帧数据。

    实际部署时：PatchBay 通常单独进程 ``await PatchBay(config).serve()``，
    各业务进程各自 ``Jack(...)`` + ``await jack.start()``。
    """
    from aiohttp.test_utils import TestServer

    from patch_bay import Jack, PatchBay

    cfg = {
        "listen": 0,
        "jacks": [
            {"name": "a", "address": "127.0.0.1:0"},
            {"name": "b", "address": "127.0.0.1:0"},
        ],
        "wires": [{"from": "a", "to": "b", "rule": "pass"}],
        "rules": {"pass": "True"},
    }
    pb = PatchBay(cfg)
    async with TestServer(pb.build_application()) as server:
        ws_url = str(server.make_url("/").with_scheme("ws"))
        loop = asyncio.get_running_loop()
        got: asyncio.Future[bytes] = loop.create_future()

        jack_b = Jack(name="b", server=ws_url)

        @jack_b
        async def _(payload: bytes) -> None:
            if not got.done():
                got.set_result(payload)

        jack_a = Jack(name="a", server=ws_url)
        await jack_a.start()
        await jack_b.start()
        await asyncio.sleep(0.2)
        await jack_a.send(b"hello from demo")
        data = await asyncio.wait_for(got, timeout=3.0)
        await jack_a.aclose()
        await jack_b.aclose()
    print("patch_bay demo ok:", data.decode())


def main() -> None:
    asyncio.run(demo())


if __name__ == "__main__":
    main()
