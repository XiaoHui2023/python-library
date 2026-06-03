from __future__ import annotations

import unittest

from ai_agent import Agent, AgentListener, ChatMessage, RunStatus, Tool
from ai_agent.context import RunContext
from ai_agent.llm import StreamChunk, StreamKind
from ai_agent.loop import ReactLoop

from tests.script_llm import ScriptLLM


class ListenerTests(unittest.IsolatedAsyncioTestCase):
    async def test_output_and_tool_callbacks(self) -> None:
        events: list[tuple[str, object]] = []

        listener = AgentListener(
            on_run_start=lambda run: events.append(("start", run.status)),
            on_output_delta=lambda delta, run: events.append(("output", delta)),
            on_tool_start=lambda inv, run: events.append(("tool_start", inv.tool_name)),
            on_tool_end=lambda inv, run: events.append(("tool_end", inv.answer)),
            on_run_end=lambda run: events.append(("end", run.status)),
        )

        agent = Agent(
            api_key="test-key",
            model="test",
            base_url="https://example.test/v1",
            listeners=listener,
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
        agent.context.llm = ScriptLLM(
            _scripts=[
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
            ]
        )

        output = await agent.run(
            messages=[ChatMessage(role="user", content="use tool")],
        )

        self.assertEqual(output, "pong")
        self.assertEqual(events[0], ("start", RunStatus.RUNNING))
        self.assertIn(("tool_start", "echo"), events)
        self.assertIn(("tool_end", "ping"), events)
        self.assertIn(("output", "pong"), events)
        self.assertEqual(events[-1], ("end", RunStatus.COMPLETED))

    async def test_multiple_listeners(self) -> None:
        seen: list[str] = []

        agent = Agent(
            api_key="test-key",
            model="test",
            base_url="https://example.test/v1",
            listeners=[
                AgentListener(on_output_delta=lambda delta, run: seen.append(f"a:{delta}")),
                AgentListener(on_output_delta=lambda delta, run: seen.append(f"b:{delta}")),
            ],
        )
        agent.context.llm = ScriptLLM(
            _scripts=[
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="hi"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ]
        )

        output = await agent.run(
            messages=[ChatMessage(role="user", content="q")],
        )

        self.assertEqual(output, "hi")
        self.assertEqual(seen, ["a:hi", "b:hi"])

    async def test_async_callback(self) -> None:
        seen: list[str] = []

        async def on_end(run: RunContext) -> None:
            seen.append(run.output)

        agent = Agent(
            api_key="test-key",
            model="test",
            base_url="https://example.test/v1",
            listeners=AgentListener(on_run_end=on_end),
        )
        agent.context.llm = ScriptLLM(
            _scripts=[
                [
                    StreamChunk(kind=StreamKind.TEXT, delta="done"),
                    StreamChunk(kind=StreamKind.DONE),
                ],
            ]
        )

        output = await agent.run(
            messages=[ChatMessage(role="user", content="q")],
        )

        self.assertEqual(output, "done")
        self.assertEqual(seen, ["done"])

    async def test_react_loop_notifies_on_failure(self) -> None:
        statuses: list[RunStatus] = []

        agent = Agent(
            api_key="test-key",
            model="test",
            base_url="https://example.test/v1",
            listeners=AgentListener(on_run_end=lambda run: statuses.append(run.status)),
        )

        class BrokenLLM(ScriptLLM):
            async def stream(self, context, tools=None):
                raise RuntimeError("boom")
                yield  # pragma: no cover

        agent.context.llm = BrokenLLM(_scripts=[])

        run = RunContext(messages=[ChatMessage(role="user", content="q")])
        loop = ReactLoop(agent.context)
        with self.assertRaises(RuntimeError):
            async for _ in loop.run(run):
                pass

        self.assertEqual(statuses, [RunStatus.FAILED])


if __name__ == "__main__":
    unittest.main()
