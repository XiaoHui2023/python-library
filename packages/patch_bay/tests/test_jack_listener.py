from __future__ import annotations

import asyncio
import unittest

from aiohttp.test_utils import TestServer

from patch_bay.codec.packet import decode_application_packet
from patch_bay.jack import Jack
from patch_bay.listeners import JackListener
from patch_bay.patchbay import PatchBay


class _Collect(JackListener):
    def __init__(self) -> None:
        self.trace: list[tuple[str, tuple]] = []

    def on_link_up(self) -> None:
        self.trace.append(("on_link_up", ()))

    def on_link_down(self) -> None:
        self.trace.append(("on_link_down", ()))

    def on_stopping(self) -> None:
        self.trace.append(("on_stopping", ()))

    def on_incoming_deliver(self, payload: bytes) -> None:
        self.trace.append(("on_incoming_deliver", (payload,)))


class TestJackListener(unittest.IsolatedAsyncioTestCase):
    async def test_listener_lifecycle_and_deliver(self) -> None:
        cfg = {
            "listen": 0,
            "jacks": [
                {"name": "a", "address": "127.0.0.1:7001"},
                {"name": "b", "address": "127.0.0.1:7002"},
            ],
            "wires": [{"from": "a", "to": "b", "rule": "pass"}],
            "rules": {"pass": "True"},
        }
        pb = PatchBay(cfg)
        app = pb.build_application()
        col = _Collect()
        async with TestServer(app) as server:
            port = server.port
            got: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

            jack_b = Jack(port, address="127.0.0.1:7002", listeners=[col])

            @jack_b
            async def _(payload: dict) -> None:
                if not got.done():
                    got.set_result(payload)

            jack_a = Jack(port, address="127.0.0.1:7001")
            await jack_a.start()
            await jack_b.start()
            await asyncio.sleep(0.2)
            self.assertIn(("on_link_up", ()), col.trace)
            await jack_a.send({"body": "ping"})
            data = await asyncio.wait_for(got, timeout=3.0)
            self.assertEqual(data, {"body": "ping"})
            deliver = next(t for t in col.trace if t[0] == "on_incoming_deliver")
            self.assertEqual(decode_application_packet(deliver[1][0]), {"body": "ping"})
            await jack_a.aclose()
            await jack_b.aclose()
        self.assertIn(("on_stopping", ()), col.trace)
        self.assertIn(("on_link_down", ()), col.trace)


if __name__ == "__main__":
    unittest.main()
