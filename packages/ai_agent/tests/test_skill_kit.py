from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.harness import Harness
from ai_agent.skill import SkillKit
from ai_agent.skill.frontmatter import compose_skill_md, split_frontmatter


class TestSkillFrontmatter(unittest.TestCase):
    def test_split_and_compose(self) -> None:
        raw = compose_skill_md(
            {"name": "demo", "description": "用于测试"},
            "# Title\n\nbody\n",
        )
        meta, body = split_frontmatter(raw)
        self.assertEqual(meta["name"], "demo")
        self.assertIn("Title", body)


class TestSkillKit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name) / "skills"
        root.mkdir()
        skill_dir = root / "demo-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            compose_skill_md(
                {"name": "demo-skill", "description": "演示 skill"},
                "# Demo\n",
            ),
            encoding="utf-8",
        )
        self._root = root
        self._kit = SkillKit({"project": root})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_catalog_for_prompt(self) -> None:
        text = self._kit.format_catalog_for_prompt()
        self.assertIn("project/demo-skill", text)
        self.assertIn("演示 skill", text)

    def test_build_tools_names(self) -> None:
        names = {t.name for t in self._kit.build_tools()}
        self.assertEqual(
            names,
            {
                "skill__load_skill",
                "skill__disable_skill",
                "skill__refresh_skills",
            },
        )


class TestHarnessSkillRoots(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self._workspace = base / "workspace"
        self._workspace.mkdir()
        skill_root = base / "skill-store"
        skill_root.mkdir()
        (skill_root / "agent-skill").mkdir()
        (skill_root / "agent-skill" / "SKILL.md").write_text(
            compose_skill_md(
                {"name": "agent-skill", "description": "harness 联调"},
                "# Agent\n",
            ),
            encoding="utf-8",
        )
        self._skill_root = skill_root
        self._harness = Harness(
            self._workspace,
            skill_roots={"store": skill_root},
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_build_skill_tools_via_harness(self) -> None:
        tools = self._harness.build_skill_tools()
        names = {t.name for t in tools}
        self.assertEqual(
            names,
            {
                "skill__load_skill",
                "skill__disable_skill",
                "skill__refresh_skills",
            },
        )

    def test_build_all_tools(self) -> None:
        names = {t.name for t in self._harness.build_all_tools()}
        self.assertIn("harness__read_file", names)
        self.assertIn("skill__load_skill", names)

    def test_skill_catalog(self) -> None:
        listing = self._harness.skill.format_catalog_for_prompt()
        self.assertIn("store/agent-skill", listing)


if __name__ == "__main__":
    unittest.main()
