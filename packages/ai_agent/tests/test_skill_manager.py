from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.context import RunContext
from ai_agent.skill import SkillManager
from ai_agent.skill.frontmatter import compose_skill_md
from ai_agent.tools import Tool


class TestSkillManager(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name) / "skills"
        root.mkdir()
        skill_dir = root / "demo-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            compose_skill_md(
                {"name": "demo-skill", "description": "演示"},
                "# Demo\n",
            ),
            encoding="utf-8",
        )
        self._root = root
        self._manager = SkillManager({"project": root})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_enable_disable_updates_tools(self) -> None:
        self._manager.enable_skill("project/demo-skill")
        self.assertIn("project/demo-skill", self._manager.enabled_skill_refs)
        self._manager.disable_skill("project/demo-skill")
        self.assertEqual(self._manager.build_enabled_tools(), [])

    def test_run_ephemeral_context(self) -> None:
        run = RunContext(system_prompt="base")
        self._manager.begin_run(run)
        self._manager.enable_skill("project/demo-skill")
        self.assertIn("# Demo", run.ephemeral_skill_context)
        self.assertIn("project/demo-skill", self._manager.run_context_skill_refs)
        self._manager.end_run()
        self.assertEqual(run.ephemeral_skill_context, "")
        self.assertEqual(self._manager.enabled_skill_refs, ())

    def test_plan_delivery_preload_on_begin_run(self) -> None:
        run = RunContext(system_prompt="base")
        self._manager.begin_plan()
        try:
            self._manager.set_plan_delivery_skills(("project/demo-skill",))
            self._manager.begin_run(run)
            self.assertIn("# Demo", run.ephemeral_skill_context)
            self.assertIn("project/demo-skill", self._manager.run_context_skill_refs)
            self._manager.end_run()
            self.assertEqual(run.ephemeral_skill_context, "")
            self.assertEqual(self._manager.enabled_skill_refs, ())
        finally:
            self._manager.end_plan()

    def test_enable_twice_in_same_run(self) -> None:
        run = RunContext()
        self._manager.begin_run(run)
        first = self._manager.enable_skill("project/demo-skill")
        second = self._manager.enable_skill("project/demo-skill")
        self.assertIn("已启用", first)
        self.assertIn("已在当前运行上下文", second)
        self._manager.end_run()

    def test_builtin_tool_on_enable(self) -> None:
        def factory() -> Tool:
            return Tool(
                name="echo",
                description="回显",
                parameters={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "additionalProperties": False,
                },
                handler=lambda text: f"echo:{text}",
            )

        tool_root = self._root / "tool-skill"
        tool_root.mkdir()
        front = (
            "---\n"
            "name: tool-skill\n"
            "description: 带子工具\n"
            "tools:\n"
            "  - name: echo\n"
            "    handler: builtin:echo\n"
            "---\n\n"
            "# T\n"
        )
        (tool_root / "SKILL.md").write_text(front, encoding="utf-8")
        manager = SkillManager({"project": self._root})
        manager.builtin_registry.register("echo", factory)
        manager.refresh()
        manager.enable_skill("project/tool-skill")
        names = {tool.name for tool in manager.build_enabled_tools()}
        self.assertIn("skill__project_tool-skill__echo", names)

    def test_management_tools_exclude_writes(self) -> None:
        names = {t.name for t in self._manager.build_management_tools()}
        self.assertEqual(len(names), 6)
        self.assertNotIn("skill__write_skill", names)
        self.assertNotIn("skill__load_skill", names)


if __name__ == "__main__":
    unittest.main()
