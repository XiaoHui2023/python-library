from __future__ import annotations

import unittest

from ai_agent.harness.prompts import PLANNING_SYSTEM_PROMPT


class TestHarnessPlanningPrompt(unittest.TestCase):
    def test_planning_prompt_content(self) -> None:
        text = PLANNING_SYSTEM_PROMPT.strip()
        self.assertIn("JSON", text)
        self.assertIn("step-1", text)
        self.assertIn("builtin__current_time", text)
        self.assertIn("勿写死具体公历日期", text)
        self.assertIn("brief", text)


if __name__ == "__main__":
    unittest.main()
