from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ai_agent
from ai_agent import Agent, ChatMessage
from ai_agent.llm import StreamChunk, StreamKind

from tests.script_llm import ScriptLLM


class AiAgentImportTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertIsNotNone(ai_agent.Agent)


class AgentSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_yields_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rule = Path(tmp) / "rule.md"
            rule.write_text("sys", encoding="utf-8")
            agent = Agent(
                api_key="test-key",
                model="test",
                base_url="https://example.test/v1",
                rule_paths=[rule],
            )
            agent.context.llm = ScriptLLM(
                _scripts=[
                    [
                        StreamChunk(kind=StreamKind.TEXT, delta="ok"),
                        StreamChunk(kind=StreamKind.DONE),
                    ]
                ]
            )
            output = await agent.run(
                messages=[ChatMessage(role="user", content="q")],
            )
        self.assertEqual(output, "ok")


if __name__ == "__main__":
    unittest.main()
