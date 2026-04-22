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
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


async def _run_pb(pb) -> None:
    await pb.serve()


async def demo() -> None:
    """两 Jack 先在本机监听，PatchBay 按配置主动连上后路由互通。"""
    from patch_bay import LoggingPatchBayListener, PatchBay
    from patch_jack import Jack, LoggingJackListener

    _configure_logging()

    ja = Jack(0, host="127.0.0.1")
    jb = Jack(0, host="127.0.0.1", listeners=[LoggingJackListener()])
    await ja.start()
    await jb.start()

    cfg = {
        "jacks": [
            {"name": "a", "address": ja.listen_address},
            {"name": "b", "address": jb.listen_address},
        ],
        "wires": [{"from": "a", "to": "b", "rule": "pass"}],
        "rules": {"pass": "True"},
    }
    pb = PatchBay(cfg, listeners=[LoggingPatchBayListener()])
    loop = asyncio.get_running_loop()
    got: asyncio.Future[dict] = loop.create_future()

    @jb
    async def _(payload: dict) -> None:
        if not got.done():
            got.set_result(payload)

    pb_task = asyncio.create_task(_run_pb(pb))
    await asyncio.sleep(0.5)
    await ja.send({"msg": "hello from demo"})
    data = await asyncio.wait_for(got, timeout=3.0)
    await pb.aclose()
    await pb_task
    await ja.aclose()
    await jb.aclose()
    print("patch_bay demo ok:", data)


def main() -> None:
    asyncio.run(demo())


if __name__ == "__main__":
    main()
