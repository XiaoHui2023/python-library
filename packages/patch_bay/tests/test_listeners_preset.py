from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from patch_bay.listeners import LoggingJackListener, LoggingPatchBayListener


class TestListenersPreset(unittest.TestCase):
    @patch("patch_bay.listeners._preset._console", None)
    def test_logging_patch_bay_smoke(self) -> None:
        log = logging.getLogger("test.pb")
        log.handlers.clear()
        log.addHandler(logging.NullHandler())
        lst = LoggingPatchBayListener(logger=log, label="PB")
        lst.on_listen_started("127.0.0.1", 8765)
        lst.on_jack_connected("a", "127.0.0.1")
        lst.on_packet_delivered("a", "b", b"hi")

    @patch("patch_bay.listeners._preset._console", None)
    def test_logging_jack_smoke(self) -> None:
        log = logging.getLogger("test.jack")
        log.handlers.clear()
        log.addHandler(logging.NullHandler())
        lst = LoggingJackListener(logger=log)
        lst.on_link_up()
        lst.on_incoming_deliver(b"x" * 40)
        lst.on_ack(1)


if __name__ == "__main__":
    unittest.main()
