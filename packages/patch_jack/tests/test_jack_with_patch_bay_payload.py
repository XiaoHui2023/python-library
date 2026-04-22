from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

import pytest
from pydantic import BaseModel

pytest.importorskip("patch_bay")

from patch_bay.patchbay import PatchBay
from patch_jack import Jack


class _Msg(BaseModel):
    n: int


async def _run_pb(pb: PatchBay) -> None:
    await pb.serve()


class TestJackWithPatchBayPayload(unittest.IsolatedAsyncioTestCase):
    async def test_pydantic_model_roundtrip(self) -> None:
        ja = Jack(0, host="127.0.0.1")
        jb = Jack(0, host="127.0.0.1")
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
        got: asyncio.Future[_Msg] = asyncio.get_running_loop().create_future()

        jack_b = jb

        @jack_b
        async def _(m: _Msg) -> None:
            if not got.done():
                got.set_result(m)

        jack_a = ja
        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)
        await jack_a.send(_Msg(n=7))
        m = await asyncio.wait_for(got, timeout=3.0)
        self.assertIsInstance(m, _Msg)
        self.assertEqual(m.n, 7)
        await pb.aclose()
        await pb_task
        await jack_a.aclose()
        await jack_b.aclose()

    async def test_type_mismatch_skips_callback(self) -> None:
        ja = Jack(0, host="127.0.0.1")
        jb = Jack(0, host="127.0.0.1")
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
        called = asyncio.Event()

        jack_b = jb

        @jack_b
        async def _(payload: int) -> None:
            called.set()

        jack_a = ja
        pb_task = asyncio.create_task(_run_pb(pb))
        await asyncio.sleep(0.5)
        with patch("patch_jack.jack.logger.error") as mock_err:
            await jack_a.send({"x": 1})
            await asyncio.sleep(0.2)
            mock_err.assert_called()
        self.assertFalse(called.is_set())
        await pb.aclose()
        await pb_task
        await jack_a.aclose()
        await jack_b.aclose()


if __name__ == "__main__":
    unittest.main()
