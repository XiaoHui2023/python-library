import json
import tempfile
import time
import unittest
from pathlib import Path

from pydantic import Field

from presisted_model import PresistedModel


class CounterState(PresistedModel):
    n: int = 0
    label: str = Field(default="")


class TestPersisted(unittest.TestCase):
    def test_load_creates_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = CounterState.load(p, debounce_seconds=0.2)
            self.assertEqual(s.n, 0)
            s._flush_persist()
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
            a._flush_persist()
            b = CounterState.load(p, debounce_seconds=0.05)
            self.assertEqual(b.n, 10)
            self.assertEqual(b.label, "x")


if __name__ == "__main__":
    unittest.main()
