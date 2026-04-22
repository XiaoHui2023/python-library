from __future__ import annotations

import logging
import unittest
from unittest.mock import patch

from patch_jack.listeners import LoggingJackListener


class TestListenersJackSmoke(unittest.TestCase):
    @patch("patch_jack.listeners._preset._console", None)
    def test_logging_jack_smoke(self) -> None:
        log = logging.getLogger("test.jack")
        log.handlers.clear()
        log.addHandler(logging.NullHandler())
        lst = LoggingJackListener(logger=log)
        lst.on_listen_started("127.0.0.1:7001")
        lst.on_link_up()
        lst.on_incoming_deliver(b"x" * 40)
        lst.on_ack(1)


if __name__ == "__main__":
    unittest.main()
