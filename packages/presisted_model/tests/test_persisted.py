import gc
import json
import tempfile
import time
import unittest
from pathlib import Path

from pydantic import Field

from presisted_model import PresistedModel
from presisted_model.persisted import _pm_flush


class CounterState(PresistedModel):
    n: int = 0
    label: str = Field(default="")


class TestPersisted(unittest.TestCase):
    def test_load_creates_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=0.2)
            self.assertEqual(s.n, 0)
            s.n = 0
            time.sleep(0.25)
            self.assertTrue(p.exists())

    def test_debounce_writes_last_value(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=0.15)
            s.n = 1
            s.n = 2
            s.n = 3
            time.sleep(0.05)
            self.assertFalse(p.exists())
            time.sleep(0.2)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["n"], 3)

    def test_reload_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            a = CounterState.load(p, debounce_seconds=0.05)
            a.n = 10
            a.label = "x"
            time.sleep(0.15)
            del a
            gc.collect()
            b = CounterState.load(p, debounce_seconds=0.05)
            self.assertEqual(b.n, 10)
            self.assertEqual(b.label, "x")

    def test_duplicate_path_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            a = CounterState.load(p, debounce_seconds=0.1)
            with self.assertRaises(ValueError):
                CounterState.load(p, debounce_seconds=0.1)
            del a
            gc.collect()
            CounterState.load(p, debounce_seconds=0.1)

    def test_exit_flush_skips_if_disk_newer_than_last_persist(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=10.0)
            s.n = 999
            p.write_text(
                '{"n": 1, "label": ""}',
                encoding="utf-8",
            )
            _pm_flush(s)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["n"], 1)

    def test_debounce_writes_after_delay_even_while_scheduling(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=0.2)
            t0 = time.monotonic()
            while time.monotonic() - t0 < 1.0:
                s.n = s.n + 1
                time.sleep(0.01)
            self.assertTrue(p.exists())
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertGreater(data["n"], 10)

    def test_debounce_second_burst_starts_new_timer(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=0.15)
            s.n = 1
            time.sleep(0.2)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["n"], 1)
            s.n = 2
            time.sleep(0.05)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["n"], 1)
            time.sleep(0.2)
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["n"], 2)


if __name__ == "__main__":
    unittest.main()
