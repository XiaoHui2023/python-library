from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from ai_agent.context import RunContext
from ai_agent.llm_openai import OpenAILLM


class OpenAILLMThinkingTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_sets_enable_thinking_from_flag(self) -> None:
        client = MagicMock()
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)

            class _Stream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return _Stream()

        client.chat.completions.create = AsyncMock(side_effect=fake_create)
        llm = OpenAILLM(
            client,
            model="test",
            base_url="https://dashscope.example/v1",
            thinking_enabled=True,
        )
        run = RunContext(system_prompt="", messages=[])
        async for _ in llm.stream(run):
            pass
        self.assertIs(captured.get("enable_thinking"), True)
        self.assertNotIn("extra_body", captured)

    async def test_stream_deepseek_thinking_uses_extra_body(self) -> None:
        client = MagicMock()
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)

            class _Stream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return _Stream()

        client.chat.completions.create = AsyncMock(side_effect=fake_create)
        llm = OpenAILLM(
            client,
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com",
            thinking_enabled=True,
        )
        run = RunContext(system_prompt="", messages=[])
        async for _ in llm.stream(run):
            pass
        self.assertNotIn("enable_thinking", captured)
        self.assertEqual(
            captured.get("extra_body"),
            {"thinking": {"type": "enabled"}},
        )

    async def test_stream_disable_thinking(self) -> None:
        client = MagicMock()
        captured: dict = {}

        async def fake_create(**kwargs):
            captured.update(kwargs)

            class _Stream:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    raise StopAsyncIteration

            return _Stream()

        client.chat.completions.create = AsyncMock(side_effect=fake_create)
        llm = OpenAILLM(client, model="test", thinking_enabled=False)
        run = RunContext(system_prompt="", messages=[])
        async for _ in llm.stream(run):
            pass
        self.assertNotIn("enable_thinking", captured)


if __name__ == "__main__":
    unittest.main()
