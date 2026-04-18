"""FSChangeHook 行为与集成测试。"""

from __future__ import annotations

import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path

import fs_change_hook
from fs_change_hook.hook import FSChangeHook


def _wait_event(ev: threading.Event, seconds: float = 5.0) -> bool:
    return ev.wait(timeout=seconds)


class TestFSChangeHook(unittest.TestCase):
    def test_package_exports(self) -> None:
        self.assertEqual(
            fs_change_hook.__all__,
            [
                "FSChangeHook",
                "FSChangeOnce",
                "OnceWatchEnd",
                "expand_watch_paths",
                "watch_paths_exist",
            ],
        )
        self.assertIs(fs_change_hook.FSChangeHook, FSChangeHook)

    def test_register_and_decorator(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "f.txt"
            p.write_text("0", encoding="utf-8")
            calls: list[str] = []

            def a() -> None:
                calls.append("a")

            hook = FSChangeHook([p])
            hook.register(a)

            @hook
            def b() -> None:
                calls.append("b")

            hit = threading.Event()

            @hook
            def c() -> None:
                calls.append("c")
                hit.set()

            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit), "expected callback")
            finally:
                hook.stop()

            self.assertIn("a", calls)
            self.assertIn("b", calls)
            self.assertIn("c", calls)

    def test_unregister(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "f.txt"
            p.write_text("0", encoding="utf-8")
            hit = threading.Event()

            def cb() -> None:
                hit.set()

            hook = FSChangeHook([p], cb)
            hook.unregister(cb)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                time.sleep(0.4)
            finally:
                hook.stop()

            self.assertFalse(hit.is_set())

    def test_sync_callback_on_file_modify(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            hit = threading.Event()

            def on_change() -> None:
                hit.set()

            hook = FSChangeHook([p], on_change)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit), "sync callback not invoked")
            finally:
                hook.stop()

    def test_async_callback_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            hit = threading.Event()

            async def on_change() -> None:
                hit.set()

            hook = FSChangeHook([p], on_change)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit, 8.0), "async callback not invoked")
            finally:
                hook.stop()

    def test_async_callback_can_await(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            hit = threading.Event()

            async def on_change() -> None:
                await asyncio.sleep(0.01)
                hit.set()

            hook = FSChangeHook([p], on_change)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit, 8.0), "async callback did not finish")
            finally:
                hook.stop()

    def test_double_start_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("x", encoding="utf-8")
            hook = FSChangeHook([p])
            hook.start()
            try:
                hook.start()
                time.sleep(0.1)
            finally:
                hook.stop()

    def test_stop_without_start_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("x", encoding="utf-8")
            hook = FSChangeHook([p])
            hook.stop()

    def test_watch_directory_recursive_child(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sub = root / "sub"
            sub.mkdir()
            child = sub / "c.txt"
            child.write_text("0", encoding="utf-8")
            hit = threading.Event()

            def on_change() -> None:
                hit.set()

            hook = FSChangeHook([root], on_change)
            hook.start()
            try:
                time.sleep(0.35)
                child.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit), "change under watched dir not seen")
            finally:
                hook.stop()

    def test_glob_paths_in_constructor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            f = base / "glob_a.txt"
            f.write_text("0", encoding="utf-8")
            pattern = str(base / "glob_*.txt")
            hit = threading.Event()

            def on_change() -> None:
                hit.set()

            hook = FSChangeHook([pattern], on_change)
            hook.start()
            try:
                time.sleep(0.25)
                f.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit), "glob-expanded path not watched")
            finally:
                hook.stop()

    def test_relative_path_with_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "app"
            root.mkdir()
            p = root / "cfg" / "x.txt"
            p.parent.mkdir(parents=True)
            p.write_text("0", encoding="utf-8")
            hit = threading.Event()

            def on_change() -> None:
                hit.set()

            hook = FSChangeHook(["cfg/x.txt"], on_change, root=root)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
                self.assertTrue(_wait_event(hit), "watch with root failed")
            finally:
                hook.stop()

    def test_negative_debounce_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                FSChangeHook([p], debounce_seconds=-0.1)

    def test_debounce_collapses_rapid_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            calls: list[int] = []

            def on_change() -> None:
                calls.append(1)

            hook = FSChangeHook([p], on_change, debounce_seconds=0.2)
            hook.start()
            try:
                time.sleep(0.25)
                for i in range(8):
                    p.write_text(str(i), encoding="utf-8")
                    time.sleep(0.02)
                time.sleep(0.45)
            finally:
                hook.stop()

            self.assertEqual(len(calls), 1)

    def test_stop_cancels_pending_debounce(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "w.txt"
            p.write_text("0", encoding="utf-8")
            calls: list[int] = []

            def on_change() -> None:
                calls.append(1)

            hook = FSChangeHook([p], on_change, debounce_seconds=1.0)
            hook.start()
            try:
                time.sleep(0.25)
                p.write_text("1", encoding="utf-8")
            finally:
                hook.stop()
            time.sleep(0.15)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
