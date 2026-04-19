from __future__ import annotations

import asyncio
import unittest

from aiohttp.test_utils import TestServer

from patch_bay.jack import Jack
from patch_bay.patchbay import PatchBay


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_send_receive_with_rule(self) -> None:
        cfg = {
            "listen": 0,
            "jacks": [
                {"name": "a", "address": "127.0.0.1:0"},
                {"name": "b", "address": "127.0.0.1:0"},
            ],
            "wires": [
                {"from": "a", "to": "b", "rule": "pass"},
            ],
            "rules": {
                "pass": "True",
            },
        }
        pb = PatchBay(cfg)
        app = pb.build_application()
        async with TestServer(app) as server:
            port = server.port
            got: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

            jack_b = Jack(port, wire_id="b")

            @jack_b
            async def _(payload: bytes) -> None:
                if not got.done():
                    got.set_result(payload)

            jack_a = Jack(port, wire_id="a")
            await jack_a.start()
            await jack_b.start()
            await asyncio.sleep(0.2)
            await jack_a.send(b"ping")
            data = await asyncio.wait_for(got, timeout=3.0)
            self.assertEqual(data, b"ping")
            await jack_a.aclose()
            await jack_b.aclose()

    async def test_rule_false_drops(self) -> None:
        cfg = {
            "listen": 0,
            "jacks": [
                {"name": "a", "address": "127.0.0.1:0"},
                {"name": "b", "address": "127.0.0.1:0"},
            ],
            "wires": [
                {"from": "a", "to": "b", "rule": "block"},
            ],
            "rules": {"block": "False"},
        }
        pb = PatchBay(cfg)
        app = pb.build_application()
        async with TestServer(app) as server:
            port = server.port
            got: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

            jack_b = Jack(port, wire_id="b")

            @jack_b
            async def _recv(_p: bytes) -> None:
                if not got.done():
                    got.set_result(_p)

            jack_a = Jack(port, wire_id="a")
            await jack_a.start()
            await jack_b.start()
            await asyncio.sleep(0.2)
            await jack_a.send(b"x")
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(got, timeout=0.4)
            await jack_a.aclose()
            await jack_b.aclose()


if __name__ == "__main__":
    unittest.main()
