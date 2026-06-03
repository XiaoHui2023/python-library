from __future__ import annotations

import unittest

from ai_agent.tools import Tool, ToolRegistry


def _echo(**_: object) -> str:
    return "ok"


class TestToolRegistry(unittest.TestCase):
    def test_layers_merge(self) -> None:
        registry = ToolRegistry()
        registry.set_base_tools(
            [Tool("base_a", "a", {"type": "object", "properties": {}}, _echo)]
        )
        registry.set_management_tools(
            [
                Tool(
                    "mgmt_b",
                    "b",
                    {"type": "object", "properties": {}},
                    _echo,
                )
            ]
        )
        names = {item["function"]["name"] for item in registry.api_tools()}
        self.assertEqual(names, {"base_a", "mgmt_b"})

    def test_duplicate_name_raises(self) -> None:
        registry = ToolRegistry()
        tool = Tool("same", "d", {"type": "object", "properties": {}}, _echo)
        registry.set_base_tools([tool])
        with self.assertRaises(ValueError):
            registry.set_management_tools([tool])


if __name__ == "__main__":
    unittest.main()
