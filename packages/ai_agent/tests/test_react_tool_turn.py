from __future__ import annotations

import unittest

from ai_agent.context import ToolInvocation
from ai_agent.react_tool_turn import (
    batch_includes_current_time,
    deferred_tool_reply,
    is_current_time_tool,
    should_defer_tool_in_batch,
)


class ReactToolTurnTests(unittest.TestCase):
    def test_is_current_time_tool(self) -> None:
        self.assertTrue(is_current_time_tool("current_time__get_current_time"))
        self.assertFalse(is_current_time_tool("cursor_cli__run_cursor_agent"))

    def test_defer_non_time_when_batch_has_time(self) -> None:
        batch = [
            ToolInvocation(call_id="1", tool_name="current_time__get_current_time"),
            ToolInvocation(call_id="2", tool_name="search__go"),
        ]
        self.assertTrue(batch_includes_current_time(batch))
        self.assertFalse(should_defer_tool_in_batch(batch[0], batch))
        self.assertTrue(should_defer_tool_in_batch(batch[1], batch))

    def test_no_defer_when_only_search(self) -> None:
        batch = [ToolInvocation(call_id="1", tool_name="search__go")]
        self.assertFalse(should_defer_tool_in_batch(batch[0], batch))

    def test_deferred_reply_non_empty(self) -> None:
        self.assertIn("未执行", deferred_tool_reply())


if __name__ == "__main__":
    unittest.main()
