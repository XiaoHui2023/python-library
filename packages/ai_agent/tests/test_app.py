from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent import AgentApp


class TestAgentApp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._app = AgentApp(
            self._root,
            api_key="test-key",
            model="test-model",
            base_url="https://example.invalid/v1",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_open_session_allocates_sub_sandbox(self) -> None:
        first = self._app.open_session("user-a")
        second = self._app.open_session("user-b")
        self.assertNotEqual(first.workspace, second.workspace)
        self.assertTrue(first.workspace.is_dir())
        self.assertTrue(second.workspace.is_dir())
        try:
            first.workspace.relative_to(self._app.sandbox_root)
            second.workspace.relative_to(self._app.sandbox_root)
        except ValueError:
            self.fail("子沙箱须在总沙箱内")

    def test_open_session_idempotent(self) -> None:
        a = self._app.open_session("same")
        b = self._app.open_session("same")
        self.assertIs(a, b)

    def test_session_harness_and_memory_layout(self) -> None:
        session = self._app.open_session("layout")
        expected_root = self._app.sandbox_root / "sessions" / "layout"
        self.assertEqual(session.workspace, expected_root)
        self.assertEqual(session.harness.workspace, expected_root / "harness")
        session.harness.write_file("in-harness.txt", content="ok")
        self.assertTrue((expected_root / "harness" / "in-harness.txt").is_file())
        mem_dir = expected_root / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / "probe.json").write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            session.harness.read_file("../memory/probe.json")

    def test_harness_isolated_between_sessions(self) -> None:
        left = self._app.open_session("left")
        right = self._app.open_session("right")
        left.harness.write_file("only-left.txt", content="x")
        with self.assertRaises(ValueError):
            right.harness.read_file("only-left.txt")

    def test_close_session(self) -> None:
        self._app.open_session("gone")
        self.assertTrue(self._app.has_session("gone"))
        self.assertTrue(self._app.close_session("gone"))
        self.assertFalse(self._app.has_session("gone"))
        self.assertIsNone(self._app.get_session("gone"))

    def test_invalid_session_id(self) -> None:
        with self.assertRaises(ValueError):
            self._app.open_session("../escape")

    def test_harness_tools_off_by_default_on_agent(self) -> None:
        session = self._app.open_session("no-harness-tools")
        registry_names = {
            entry["function"]["name"]
            for entry in session.agent.context.tools.api_tools()
        }
        self.assertFalse(any(name.startswith("harness__") for name in registry_names))

    def test_harness_tools_on_agent_when_enabled(self) -> None:
        app = AgentApp(
            self._root / "with-harness",
            api_key="test-key",
            model="test-model",
            base_url="https://example.invalid/v1",
            harness_enabled=True,
        )
        session = app.open_session("tools")
        names = {t.name for t in session.harness.build_tools()}
        self.assertIn("harness__read_file", names)
        registry_names = {
            entry["function"]["name"]
            for entry in session.agent.context.tools.api_tools()
        }
        self.assertIn("harness__read_file", registry_names)

    def test_skill_management_tools_readonly_repo(self) -> None:
        with tempfile.TemporaryDirectory() as skill_tmp:
            skill_root = Path(skill_tmp)
            app = AgentApp(
                self._root / "skill-app",
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                skill_roots=[skill_root],
            )
            session = app.open_session("s1")
            names = {t.name for t in session.harness.build_skill_tools()}
            self.assertIn("skill__list_skills", names)
            self.assertNotIn("skill__write_skill", names)
            self.assertNotIn("skill__load_skill", names)


if __name__ == "__main__":
    unittest.main()
