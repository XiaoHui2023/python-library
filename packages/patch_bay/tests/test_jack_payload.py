from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from aiohttp.test_utils import TestServer
from pydantic import BaseModel

from patch_bay.jack import Jack
from patch_bay.patchbay import PatchBay


class _Msg(BaseModel):
    n: int


class TestJackPayload(unittest.IsolatedAsyncioTestCase):
    async def test_pydantic_model_roundtrip(self) -> None:
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
        async with TestServer(app) as server:
            port = server.port
            got: asyncio.Future[_Msg] = asyncio.get_running_loop().create_future()

            jack_b = Jack(port, address="127.0.0.1:7002")

            @jack_b
            async def _(m: _Msg) -> None:
                if not got.done():
                    got.set_result(m)

            jack_a = Jack(port, address="127.0.0.1:7001")
            await jack_a.start()
            await jack_b.start()
            await asyncio.sleep(0.2)
            await jack_a.send(_Msg(n=7))
            m = await asyncio.wait_for(got, timeout=3.0)
            self.assertIsInstance(m, _Msg)
            self.assertEqual(m.n, 7)
            await jack_a.aclose()
            await jack_b.aclose()

    async def test_type_mismatch_skips_callback(self) -> None:
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
        async with TestServer(app) as server:
            port = server.port
            called = asyncio.Event()

            jack_b = Jack(port, address="127.0.0.1:7002")

            @jack_b
            async def _(payload: int) -> None:
                called.set()

            jack_a = Jack(port, address="127.0.0.1:7001")
            await jack_a.start()
            await jack_b.start()
            await asyncio.sleep(0.2)
            with patch("patch_bay.jack.logger.error") as mock_err:
                await jack_a.send({"x": 1})
                await asyncio.sleep(0.15)
                mock_err.assert_called()
            self.assertFalse(called.is_set())
            await jack_a.aclose()
            await jack_b.aclose()


if __name__ == "__main__":
    unittest.main()
