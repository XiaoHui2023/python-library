from __future__ import annotations

import unittest

from ai_agent import Agent, ChatMessage, RunStatus, Tool
from ai_agent.context import RunContext
from ai_agent.llm import StreamChunk, StreamKind
from ai_agent.builtin_tools.current_time import build_current_time_tool
from ai_agent.loop import ReactLoop

from script_llm import ScriptLLM


def _agent_with_script(
    scripts: list[list[StreamChunk]],
    tools: list[Tool] | None = None,
) -> Agent:
    agent = Agent(api_key="test-key", model="test", base_url="https://example.test/v1")
    agent.context.llm = ScriptLLM(_scripts=list(scripts))
    if tools is not None:
        from ai_agent.tools import ToolRegistry

        agent.context.tools = ToolRegistry(tools)
    return agent


class ReactLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_final_answer_completes(self) -> None:
        agent = _agent_with_script(
            [
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="hello"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ]
        )
        output = await agent.run(
            messages=[ChatMessage(role="user", content="hi")],
        )
        self.assertEqual(output, "hello")

    async def test_tool_then_final(self) -> None:
        agent = _agent_with_script(
            [
                [
                    StreamChunk(
                        kind=StreamKind.TOOL_CALL,
                        tool_call_id="c1",
                        tool_name="echo",
                        tool_arguments={"text": "ping"},
                    ),
                    StreamChunk(kind=StreamKind.DONE),
                ],
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="pong"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ],
            tools=[
                Tool(
                    name="echo",
                    description="回显",
                    parameters={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                    handler=lambda text="": text,
                ),
            ],
        )
        run = RunContext(
            system_prompt="",
            messages=[ChatMessage(role="user", content="use tool")],
        )
        loop = ReactLoop(agent.context)
        ctx = None
        async for ctx in loop.run(run):
            pass
        assert ctx is not None
        self.assertEqual(ctx.status, RunStatus.COMPLETED)
        self.assertEqual(ctx.output, "pong")
        self.assertEqual(len(ctx.tool_invocations), 1)
        self.assertEqual(ctx.tool_invocations[0].answer, "ping")

    async def test_tool_turn_clears_intermediate_text_from_output(self) -> None:
        agent = _agent_with_script(
            [
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="先说明一下。"),
                    StreamChunk(
                        kind=StreamKind.TOOL_CALL,
                        tool_call_id="c1",
                        tool_name="echo",
                        tool_arguments={"text": "ping"},
                    ),
                    StreamChunk(kind=StreamKind.DONE),
                ],
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="最终结论。"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ],
            tools=[
                Tool(
                    name="echo",
                    description="回显",
                    parameters={
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                    },
                    handler=lambda text="": text,
                ),
            ],
        )
        run = RunContext(
            system_prompt="",
            messages=[ChatMessage(role="user", content="use tool")],
        )
        loop = ReactLoop(agent.context)
        ctx = None
        async for ctx in loop.run(run):
            pass
        assert ctx is not None
        self.assertEqual(ctx.output, "最终结论。")

    async def test_same_turn_search_deferred_until_after_current_time(self) -> None:
        search_calls: list[dict[str, object]] = []

        def _search(*, query: str = "") -> str:
            search_calls.append({"query": query})
            return f"hit:{query}"

        agent = _agent_with_script(
            [
                [
                    StreamChunk(
                        kind=StreamKind.TOOL_CALL,
                        tool_call_id="t1",
                        tool_name="builtin__current_time",
                        tool_arguments={},
                    ),
                    StreamChunk(
                        kind=StreamKind.TOOL_CALL,
                        tool_call_id="s1",
                        tool_name="search__go",
                        tool_arguments={"query": "wrong-date"},
                    ),
                    StreamChunk(kind=StreamKind.DONE),
                ],
                [
                    StreamChunk(
                        kind=StreamKind.TOOL_CALL,
                        tool_call_id="s2",
                        tool_name="search__go",
                        tool_arguments={"query": "fixed"},
                    ),
                    StreamChunk(kind=StreamKind.DONE),
                ],
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="done"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ],
            tools=[
                build_current_time_tool(),
                Tool(
                    name="search__go",
                    description="搜索",
                    parameters={
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                    handler=_search,
                ),
            ],
        )
        run = RunContext(
            system_prompt="",
            messages=[ChatMessage(role="user", content="搜今天")],
        )
        loop = ReactLoop(agent.context)
        ctx = None
        async for ctx in loop.run(run):
            pass
        assert ctx is not None
        self.assertEqual(len(search_calls), 1)
        self.assertEqual(search_calls[0]["query"], "fixed")
        deferred = [
            inv
            for inv in ctx.tool_invocations
            if inv.tool_name == "search__go" and "未执行" in inv.answer
        ]
        self.assertEqual(len(deferred), 1)
        self.assertEqual(deferred[0].arguments["query"], "wrong-date")


if __name__ == "__main__":
    unittest.main()
