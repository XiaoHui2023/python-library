from __future__ import annotations

import unittest

from ai_agent.context import ChatMessage, RunContext, ToolInvocation


class ApiMessagesTests(unittest.TestCase):
    def test_tool_turn_includes_assistant_tool_calls(self) -> None:
        run = RunContext(
            messages=[ChatMessage(role="user", content="几点了")],
            tool_turns=[
                [
                    ToolInvocation(
                        call_id="c1",
                        tool_name="current_time__get_current_time",
                        arguments={"timezone": "Asia/Shanghai"},
                        thinking="先查上海时间",
                        answer="2026-06-01T22:09:56+08:00",
                    ),
                ],
            ],
        )

        messages = run.api_messages()

        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertEqual(messages[1]["content"], "先查上海时间")
        self.assertEqual(len(messages[1]["tool_calls"]), 1)
        self.assertEqual(
            messages[1]["tool_calls"][0]["function"]["name"],
            "current_time__get_current_time",
        )
        self.assertEqual(messages[2]["role"], "tool")
        self.assertEqual(messages[2]["tool_call_id"], "c1")
        self.assertEqual(messages[2]["content"], "2026-06-01T22:09:56+08:00")


if __name__ == "__main__":
    unittest.main()
