from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ai_agent import AgentApp
from ai_agent.llm import StreamChunk, StreamKind
from ai_agent.plan.delivery import delivery_skill_refs_for_step
from ai_agent.plan.models import PlanStep
from ai_agent.skill.frontmatter import compose_skill_md

from script_llm import ScriptLLM


class TestPlanDelivery(unittest.TestCase):
    def test_delivery_skill_refs_from_path(self) -> None:
        step = PlanStep(
            id="step-2",
            title="改写",
            objective="按 skills/chat-search-answer 交付终稿",
        )
        self.assertEqual(
            delivery_skill_refs_for_step(step),
            ("skills/chat-search-answer",),
        )

    def test_delivery_skill_refs_from_alias(self) -> None:
        step = PlanStep(
            id="step-2",
            title="改写",
            objective="启用 chat-search-answer 技能改写",
        )
        self.assertEqual(
            delivery_skill_refs_for_step(step),
            ("skills/chat-search-answer",),
        )


class TestPlanRunnerDeliveryPreload(unittest.IsolatedAsyncioTestCase):
    async def test_last_step_preloads_skill_without_enable_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_root = root / "skills"
            skill_dir = skills_root / "chat-search-answer"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                compose_skill_md(
                    {"name": "chat-search-answer", "description": "改写"},
                    "# Rewrite\n",
                ),
                encoding="utf-8",
            )
            rule_file = root / "rules.md"
            rule_file.write_text("规则", encoding="utf-8")
            plan_json = json.dumps(
                {
                    "steps": [
                        {
                            "id": "step-1",
                            "title": "搜索",
                            "objective": "搜索",
                        },
                        {
                            "id": "step-2",
                            "title": "终稿",
                            "objective": "按 skills/chat-search-answer 交付",
                            "required_tool": "enable_skill",
                        },
                    ],
                },
                ensure_ascii=False,
            )
            final_json = json.dumps(
                {"answer": "终稿", "output_files": []},
                ensure_ascii=False,
            )
            llm = ScriptLLM(
                _scripts=[
                    [StreamChunk(kind=StreamKind.TEXT, delta=plan_json)],
                    [StreamChunk(kind=StreamKind.TEXT, delta="要点")],
                    [StreamChunk(kind=StreamKind.TEXT, delta=final_json)],
                ],
            )
            app = AgentApp(
                tmp,
                skill_roots={"skills": skills_root},
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
            )
            session = app.open_session("delivery-preload")
            session.agent.context.llm = llm
            result = await session.run_with_plan(user_message="搜新闻")
        self.assertEqual(result.final_output, final_json)
        manager = session.skill_manager
        assert manager is not None
        self.assertEqual(manager.enabled_skill_refs, ())


if __name__ == "__main__":
    unittest.main()
