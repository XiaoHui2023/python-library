from __future__ import annotations



import json

import tempfile

import unittest

from pathlib import Path



from ai_agent import AgentApp

from ai_agent.llm import StreamChunk, StreamKind

from ai_agent import AgentListener
from ai_agent.plan import PlanParseError, parse_plan_text
from ai_agent.plan.complete import complete_text
from ai_agent.plan.display import format_plan_for_terminal
from ai_agent.plan.planner import PlanPlanner
from ai_agent.memory import MemoryConfig, MemorySystem

from script_llm import ScriptLLM





class TestPlanParse(unittest.TestCase):

    def test_parse_json_object(self) -> None:

        payload = {

            "summary": "demo",

            "steps": [

                {

                    "id": "step-1",

                    "title": "A",

                    "objective": "do a",

                },

            ],

        }

        plan = parse_plan_text(json.dumps(payload, ensure_ascii=False))

        self.assertEqual(len(plan.steps), 1)

        self.assertEqual(plan.steps[0].id, "step-1")



    def test_parse_with_fence(self) -> None:

        inner = '{"steps": [{"id": "s1", "title": "t", "objective": "o"}]}'

        plan = parse_plan_text(f"```json\n{inner}\n```")

        self.assertEqual(plan.steps[0].id, "s1")

    def test_parse_trailing_prose(self) -> None:
        payload = {
            "steps": [{"id": "step-1", "title": "A", "objective": "do a"}],
        }
        inner = json.dumps(payload, ensure_ascii=False)
        plan = parse_plan_text(f"{inner}\n\n以上是执行计划。")
        self.assertEqual(plan.steps[0].id, "step-1")

    def test_parse_two_objects_uses_first(self) -> None:
        first = {
            "steps": [{"id": "step-1", "title": "A", "objective": "do a"}],
        }
        second = {"note": "ignored"}
        text = json.dumps(first, ensure_ascii=False) + json.dumps(
            second,
            ensure_ascii=False,
        )
        plan = parse_plan_text(text)
        self.assertEqual(plan.steps[0].id, "step-1")

    def test_parse_hint_tools_null(self) -> None:
        payload = {
            "steps": [
                {
                    "id": "step-1",
                    "title": "回复",
                    "objective": "回答用户",
                    "hint_tools": None,
                    "required_tool": None,
                },
            ],
        }
        plan = parse_plan_text(json.dumps(payload, ensure_ascii=False))
        self.assertEqual(plan.steps[0].hint_tools, [])
        self.assertIsNone(plan.steps[0].required_tool)

    def test_parse_empty_raises(self) -> None:

        with self.assertRaises(PlanParseError):

            parse_plan_text("   ")


class TestPlanDisplay(unittest.TestCase):
    def test_format_plan_for_terminal(self) -> None:
        payload = {
            "summary": "演示计划",
            "steps": [
                {
                    "id": "step-1",
                    "title": "第一步",
                    "objective": "完成 A",
                    "hint_tools": ["search"],
                },
                {
                    "id": "step-2",
                    "title": "第二步",
                    "objective": "完成 B",
                    "optional": True,
                },
            ],
        }
        plan = parse_plan_text(json.dumps(payload, ensure_ascii=False))
        text = format_plan_for_terminal(plan)
        self.assertIn("--- plan ---", text)
        self.assertIn("摘要: 演示计划", text)
        self.assertIn("步骤（共 2 步）", text)
        self.assertIn("1. step-1 · 第一步", text)
        self.assertIn("建议工具: search", text)
        self.assertIn("2. step-2 · 第二步（可选）", text)


class TestPlanCompleteText(unittest.IsolatedAsyncioTestCase):
    async def test_parse_from_answer_text_only_ignores_reasoning_json(self) -> None:
        draft = json.dumps(
            {
                "steps": [
                    {
                        "id": "step-1",
                        "title": "草稿",
                        "objective": "不应采用",
                    },
                ],
            },
            ensure_ascii=False,
        )
        final = json.dumps(
            {
                "steps": [
                    {
                        "id": "step-1",
                        "title": "正式",
                        "objective": "应采用",
                    },
                ],
            },
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [
                    StreamChunk(kind=StreamKind.REASONING, delta=draft),
                    StreamChunk(kind=StreamKind.TEXT, delta=final),
                ],
            ],
        )
        text = await complete_text(
            llm,
            system_prompt="规划",
            user_content="分解任务",
            parse_from_answer_text_only=True,
        )
        plan = parse_plan_text(text)
        self.assertEqual(plan.steps[0].title, "正式")

    async def test_planner_uses_answer_text_only(self) -> None:
        draft = json.dumps(
            {
                "steps": [
                    {"id": "step-1", "title": "草稿", "objective": "x"},
                ],
            },
            ensure_ascii=False,
        )
        final = json.dumps(
            {
                "steps": [
                    {"id": "step-1", "title": "正式", "objective": "y"},
                ],
            },
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [
                    StreamChunk(kind=StreamKind.REASONING, delta=draft),
                    StreamChunk(kind=StreamKind.TEXT, delta=final),
                ],
            ],
        )
        planner = PlanPlanner(llm)
        plan = await planner.plan(
            user_message="你好",
            business_system_prompt="规则",
            messages=[],
        )
        self.assertEqual(plan.steps[0].title, "正式")


class TestPlanRunner(unittest.IsolatedAsyncioTestCase):

    async def test_run_with_plan_serial(self) -> None:

        plan_json = json.dumps(

            {

                "steps": [

                    {"id": "step-1", "title": "一步", "objective": "回答 A"},

                    {"id": "step-2", "title": "二步", "objective": "回答 B"},

                ],

            },

            ensure_ascii=False,

        )

        llm = ScriptLLM(

            _scripts=[

                [StreamChunk(kind=StreamKind.TEXT, delta=plan_json)],

                [StreamChunk(kind=StreamKind.TEXT, delta="输出 A")],

                [StreamChunk(kind=StreamKind.TEXT, delta="输出 B")],

            ],

        )

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(tmp)

            rule_file = root / "rules.md"

            rule_file.write_text("你是助手", encoding="utf-8")

            app = AgentApp(

                tmp,

                rule_paths=[rule_file],

                api_key="k",

                model="m",

                base_url="https://example.invalid/v1",

            )

            session = app.open_session("plan-demo")

            session.agent.context.llm = llm

            result = await session.run_with_plan(

                user_message="你好",

            )

        self.assertEqual(len(result.plan.steps), 2)

        self.assertEqual(result.step_outputs["step-1"], "输出 A")

        self.assertEqual(result.final_output, "输出 B")

        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[-1].content, "输出 B")

    async def test_finish_plan_run_stores_parsed_answer_in_memory(self) -> None:
        plan_json = json.dumps(
            {
                "steps": [
                    {"id": "step-1", "title": "一步", "objective": "回答"},
                ],
            },
            ensure_ascii=False,
        )
        final_json = json.dumps(
            {"answer": "记忆正文", "output_files": []},
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta=plan_json)],
                [StreamChunk(kind=StreamKind.TEXT, delta=final_json)],
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rule_file = root / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            memory = MemorySystem(
                root / "memory",
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                config=MemoryConfig(short_term_max_messages=20),
                autostart=False,
                use_llm_compressor=False,
            )
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                memory_api_key="k",
                memory_model="m",
                memory_base_url="https://example.invalid/v1",
            )
            session = app.open_session("mem-plan", memory=memory)
            session.agent.context.llm = llm
            await session.run_with_plan(user_message="你好", speaker="Alice")
            snap = memory._copy_agent_view()
        assistant_rows = [
            m for m in snap.short_term if m.role == "assistant"
        ]
        self.assertEqual(len(assistant_rows), 1)
        self.assertEqual(assistant_rows[0].content, "记忆正文")

    async def test_plan_listener_callbacks(self) -> None:
        plan_json = json.dumps(
            {
                "steps": [
                    {"id": "step-1", "title": "一步", "objective": "回答"},
                ],
            },
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta=plan_json)],
                [StreamChunk(kind=StreamKind.TEXT, delta="完成")],
            ],
        )
        events: list[str] = []
        listener = AgentListener(
            on_plan_start=lambda: events.append("plan_start"),
            on_plan_ready=lambda plan: events.append(f"plan_ready:{len(plan.steps)}"),
            on_plan_step_start=lambda idx, step, plan: events.append(
                f"step_start:{idx}:{step.id}",
            ),
            on_plan_step_end=lambda idx, step, plan, output, skipped: events.append(
                f"step_end:{idx}:{skipped}",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rule_file = root / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                listeners=listener,
            )
            session = app.open_session("plan-listener")
            session.agent.context.llm = llm
            await session.run_with_plan(user_message="你好")
        self.assertEqual(
            events,
            [
                "plan_start",
                "plan_ready:1",
                "step_start:0:step-1",
                "step_end:0:False",
            ],
        )


if __name__ == "__main__":

    unittest.main()


