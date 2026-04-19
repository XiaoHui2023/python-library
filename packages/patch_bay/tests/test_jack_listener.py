from __future__ import annotations

import asyncio
import unittest

from patch_bay.codec.packet import decode_application_packet
from patch_bay.jack import Jack
from patch_bay.listeners import JackListener
from patch_bay.patchbay import PatchBay


async def _run_pb(pb: PatchBay) -> None:
    await pb.serve()


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
        col = _Collect()
        ja = Jack(0, host="127.0.0.1")
        jb = Jack(0, host="127.0.0.1", listeners=[col])
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
        pb = PatchBay(cfg)
        got: asyncio.Future[dict] = asyncio.get_running_loop().create_future()

        @jb
        async def _(payload: dict) -> None:
            if not got.done():
                got.set_result(payload)

        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)
        self.assertIn(("on_link_up", ()), col.trace)
        await ja.send({"body": "ping"})
        data = await asyncio.wait_for(got, timeout=3.0)
        self.assertEqual(data, {"body": "ping"})
        deliver = next(t for t in col.trace if t[0] == "on_incoming_deliver")
        self.assertEqual(decode_application_packet(deliver[1][0]), {"body": "ping"})
        await pb.aclose()
        await pb_task
        await ja.aclose()
        await jb.aclose()
        self.assertIn(("on_stopping", ()), col.trace)
        self.assertIn(("on_link_down", ()), col.trace)


if __name__ == "__main__":
    unittest.main()
