from __future__ import annotations

import logging
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from watch_config import ChangeLog, ChangeRenderer, WatchConfig


class BoomRenderer(ChangeRenderer):
    def render(self, changelog: ChangeLog) -> str:
        raise RuntimeError("render boom")


class WatchConfigTests(unittest.TestCase):
    def _write_yaml(self, path: Path, content: str) -> None:
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def test_start_loads_file_and_sets_value(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "cfg.yaml"
            self._write_yaml(p, "x: 1\ny: two")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            try:
                w.start()
                self.assertIsNotNone(w.value)
                self.assertEqual(w.value, {"x": 1, "y": "two"})
                self.assertEqual(w.file_path, p.resolve())
            finally:
                w.stop()

    def test_decorator_registers_callbacks(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "n: 0")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            seen: list[tuple[Any, ChangeLog]] = []

            @w
            def cb(cfg: dict, changelog: ChangeLog) -> None:
                seen.append((dict(cfg), changelog))

            try:
                w.start()
                self.assertEqual(len(seen), 1)
                self.assertEqual(seen[0][0], {"n": 0})
                self.assertTrue(seen[0][1].is_empty)
            finally:
                w.stop()

    def test_callback_zero_or_one_arg(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "a: 1")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            calls: list[str] = []

            @w
            def cb0() -> None:
                calls.append("0")

            @w
            def cb1(cfg: dict) -> None:
                calls.append("1")

            try:
                w.start()
                self.assertEqual(sorted(calls), ["0", "1"])
            finally:
                w.stop()

    def test_reload_after_file_change_non_empty_changelog(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "k: 1")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            try:
                w.start()
                self._write_yaml(p, "k: 2")
                time.sleep(0.05)
                log = w.reload()
                self.assertFalse(log.is_empty)
                self.assertEqual(w.value, {"k": 2})
            finally:
                w.stop()

    def test_set_path_reloads(self) -> None:
        with TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.yaml"
            p2 = Path(tmp) / "b.yaml"
            self._write_yaml(p1, "u: 1")
            self._write_yaml(p2, "u: 2")
            w = WatchConfig(p1, dict, interval=0.05, debounce=0.05)
            try:
                w.start()
                self.assertEqual(w.value, {"u": 1})
                w.set_path(p2)
                self.assertEqual(w.file_path, p2.resolve())
                self.assertEqual(w.value, {"u": 2})
            finally:
                w.stop()

    def test_has_changed_false_when_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "missing.yaml"
            w = WatchConfig(p, dict)
            self.assertFalse(w.has_changed())

    def test_has_changed_after_write(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "a: 1")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            try:
                w.start()
                self.assertFalse(w.has_changed())
                self._write_yaml(p, "a: 2")
                self.assertTrue(w.has_changed())
            finally:
                w.stop()

    def test_double_start_is_idempotent(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "z: 1")
            w = WatchConfig(p, dict, interval=0.05, debounce=0.05)
            try:
                w.start()
                t1 = w._thread
                w.start()
                self.assertIs(w._thread, t1)
            finally:
                w.stop()

    def test_renderer_failure_still_invokes_callbacks(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "c.yaml"
            self._write_yaml(p, "q: 1")
            logger = logging.getLogger("test_watch_renderer_fail")
            logger.handlers.clear()
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            logger.setLevel(logging.ERROR)
            w = WatchConfig(
                p,
                dict,
                renderer=BoomRenderer(),
                interval=0.05,
                debounce=0.05,
                logger_=logger,
            )
            ok: list[bool] = []

            @w
            def cb(cfg: dict) -> None:
                ok.append(True)

            try:
                w.start()
                self._write_yaml(p, "q: 2")
                w.reload()
                self.assertEqual(ok, [True, True])
            finally:
                w.stop()

    def test_reload_raises_propagates_to_caller(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.yaml"
            p.write_text("{ not yaml", encoding="utf-8")
            w = WatchConfig(p, dict)
            with self.assertRaises(Exception):
                w.reload()


if __name__ == "__main__":
    unittest.main()
