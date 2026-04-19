from __future__ import annotations

import asyncio
import unittest

from patch_bay.jack import Jack
from patch_bay.patchbay import PatchBay


async def _run_pb(pb: PatchBay) -> None:
    await pb.serve()


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_send_receive_with_rule(self) -> None:
        ja = Jack(0, host="127.0.0.1")
        jb = Jack(0, host="127.0.0.1")
        await ja.start()
        await jb.start()
        cfg = {
            "jacks": [
                {"name": "a", "address": ja.listen_address},
                {"name": "b", "address": jb.listen_address},
            ],
            "wires": [
                {"from": "a", "to": "b", "rule": "pass"},
            ],
            "rules": {
                "pass": "True",
            },
        }
        pb = PatchBay(cfg)
        got: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

        jack_b = jb

        @jack_b
        async def _(payload: dict) -> None:
            if not got.done():
                got.set_result(payload)

        jack_a = ja
        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)
        await jack_a.send({"body": "ping"})
        data = await asyncio.wait_for(got, timeout=3.0)
        self.assertEqual(data, {"body": "ping"})
        await pb.aclose()
        await pb_task
        await jack_a.aclose()
        await jack_b.aclose()

    async def test_rule_false_drops(self) -> None:
        ja = Jack(0, host="127.0.0.1")
        jb = Jack(0, host="127.0.0.1")
        await ja.start()
        await jb.start()
        cfg = {
            "jacks": [
                {"name": "a", "address": ja.listen_address},
                {"name": "b", "address": jb.listen_address},
            ],
            "wires": [
                {"from": "a", "to": "b", "rule": "block"},
            ],
            "rules": {"block": "False"},
        }
        pb = PatchBay(cfg)
        got: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

        jack_b = jb

        @jack_b
        async def _recv(_p: dict) -> None:
            if not got.done():
                got.set_result(_p)

        jack_a = ja
        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)
        await jack_a.send({"x": 1})
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(got, timeout=0.4)
        await pb.aclose()
        await pb_task
        await jack_a.aclose()
        await jack_b.aclose()


if __name__ == "__main__":
    unittest.main()
