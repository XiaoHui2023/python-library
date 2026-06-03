from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent import AgentApp
from ai_agent.builtin_tools import build_current_time_tool, harness_current_time_tool_name


class TestBuiltinCurrentTimeTool(unittest.IsolatedAsyncioTestCase):
    async def test_tool_returns_iso_timestamp(self) -> None:
        tool = build_current_time_tool()
        ok, text = await tool.run({})
        self.assertTrue(ok)
        self.assertRegex(text, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    async def test_invalid_timezone_fails(self) -> None:
        tool = build_current_time_tool()
        ok, text = await tool.run({"timezone": "Not/A/Zone"})
        self.assertFalse(ok)
        self.assertIn("未知时区", text)


class TestAgentAppBuiltinTools(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_current_time_on_by_default(self) -> None:
        app = AgentApp(
            self._root,
            api_key="test-key",
            model="test-model",
            base_url="https://example.invalid/v1",
        )
        session = app.open_session("t")
        names = {
            entry["function"]["name"]
            for entry in session.agent.context.tools.api_tools()
        }
        self.assertIn("builtin__current_time", names)

    def test_current_time_can_disable(self) -> None:
        app = AgentApp(
            self._root,
            api_key="test-key",
            model="test-model",
            base_url="https://example.invalid/v1",
            current_time_tool_enabled=False,
        )
        session = app.open_session("t")
        names = {
            entry["function"]["name"]
            for entry in session.agent.context.tools.api_tools()
        }
        self.assertNotIn("builtin__current_time", names)

    def test_harness_on_uses_builtin_current_time_not_duplicate(self) -> None:
        app = AgentApp(
            self._root,
            api_key="k",
            model="m",
            base_url="https://example.invalid/v1",
            harness_enabled=True,
            current_time_tool_enabled=True,
        )
        session = app.open_session("both")
        names = {
            entry["function"]["name"]
            for entry in session.agent.context.tools.api_tools()
        }
        self.assertIn("builtin__current_time", names)
        self.assertNotIn(harness_current_time_tool_name(), names)
        self.assertIn("harness__read_file", names)


if __name__ == "__main__":
    unittest.main()
