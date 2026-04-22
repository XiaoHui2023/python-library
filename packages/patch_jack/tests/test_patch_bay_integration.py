from __future__ import annotations

import asyncio
import unittest

import pytest

pytest.importorskip("patch_bay")

from patch_bay.patchbay import PatchBay
from patch_jack import Jack


async def _run_pb(pb: PatchBay) -> None:
    await pb.serve()


class TestPatchBayIntegration(unittest.IsolatedAsyncioTestCase):
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

    async def test_four_endpoints_two_inputs_two_outputs_isolated(self) -> None:
        """四端点：in1→out1、in2→out2，两路分别投递且互不串包。"""
        in1 = Jack(0, host="127.0.0.1")
        out1 = Jack(0, host="127.0.0.1")
        in2 = Jack(0, host="127.0.0.1")
        out2 = Jack(0, host="127.0.0.1")
        await in1.start()
        await out1.start()
        await in2.start()
        await out2.start()

        cfg = {
            "jacks": [
                {"name": "in1", "address": in1.listen_address},
                {"name": "out1", "address": out1.listen_address},
                {"name": "in2", "address": in2.listen_address},
                {"name": "out2", "address": out2.listen_address},
            ],
            "wires": [
                {"from": "in1", "to": "out1"},
                {"from": "in2", "to": "out2"},
            ],
            "rules": {},
        }
        pb = PatchBay(cfg)

        received_out1: list[dict] = []
        received_out2: list[dict] = []

        @out1
        async def _recv1(payload: dict) -> None:
            received_out1.append(payload)

        @out2
        async def _recv2(payload: dict) -> None:
            received_out2.append(payload)

        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)

        await in1.send({"lane": "a", "n": 1})
        await in2.send({"lane": "b", "n": 2})
        await asyncio.sleep(0.3)

        self.assertEqual(received_out1, [{"lane": "a", "n": 1}])
        self.assertEqual(received_out2, [{"lane": "b", "n": 2}])

        await pb.aclose()
        await pb_task
        await in1.aclose()
        await out1.aclose()
        await in2.aclose()
        await out2.aclose()


if __name__ == "__main__":
    unittest.main()
