from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

import msgpack

from patch_bay.listeners import LoggingPatchBayListener
from patch_bay.listeners._preset import _payload_preview


class TestListenersPreset(unittest.TestCase):
    def test_payload_preview_msgpack_dict(self) -> None:
        b = msgpack.packb({"msg": "hello from demo"}, use_bin_type=True)
        s = _payload_preview(b)
        self.assertIn("msg", s)
        self.assertIn("hello from demo", s)
        self.assertNotIn("[二进制]", s)

    @patch("patch_bay.listeners._preset._console", None)
    def test_logging_patch_bay_smoke(self) -> None:
        log = logging.getLogger("test.pb")
        log.handlers.clear()
        log.addHandler(logging.NullHandler())
        lst = LoggingPatchBayListener(logger=log, label="PB")
        lst.on_listen_started("127.0.0.1", 8765)
        lst.on_jack_connected("a", "127.0.0.1")
        lst.on_packet_delivered("a", "b", b"hi")


if __name__ == "__main__":
    unittest.main()
