from __future__ import annotations

import logging
import unittest

from watch_config import ChangeLog, ChangeType, DefaultRenderer


class DefaultRendererTests(unittest.TestCase):
    def test_empty_changelog_returns_empty_string(self) -> None:
        r = DefaultRenderer(color=False)
        self.assertEqual(r.render(ChangeLog()), "")

    def test_render_contains_paths_and_icons(self) -> None:
        log = ChangeLog()
        log.added("$.foo", {"k": 1})
        log.removed("$.bar", 2)
        log.updated("$.baz", 0, 1)

        r = DefaultRenderer(color=False, max_value_length=200)
        text = r.render(log)

        self.assertIn("Config Changes (3):", text)
        self.assertIn("+ foo", text)
        self.assertIn("- bar", text)
        self.assertIn("~ baz", text)

    def test_emit_logs_when_non_empty(self) -> None:
        log = ChangeLog()
        log.added("$.x", 1)
        r = DefaultRenderer(color=False)
        logger = logging.getLogger("test_renderer_emit")
        logger.setLevel(logging.INFO)
        with self.assertLogs(logger, level="INFO") as cm:
            r.emit(log, logger)
        self.assertTrue(any("Config Changes" in rec.message for rec in cm.records))

    def test_emit_skips_empty_string(self) -> None:
        r = DefaultRenderer(color=False)
        logger = logging.getLogger("test_renderer_emit_empty")
        logger.setLevel(logging.INFO)
        with self.assertLogs(logger, level="INFO") as cm:
            logger.info("marker")
            r.emit(ChangeLog(), logger)
        self.assertEqual(len(cm.records), 1)
        self.assertIn("marker", cm.records[0].getMessage())

    def test_long_value_truncated(self) -> None:
        log = ChangeLog()
        log.added("$.v", "x" * 100)
        r = DefaultRenderer(color=False, max_value_length=20)
        text = r.render(log)
        self.assertIn("...", text)


if __name__ == "__main__":
    unittest.main()
