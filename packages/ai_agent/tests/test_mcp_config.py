from __future__ import annotations

import unittest

from pydantic import ValidationError

from ai_agent.mcp_config import McpConfig, parse_mcp_config


class McpConfigTests(unittest.TestCase):
    def test_parse_from_mapping_with_alias(self) -> None:
        config = parse_mcp_config(
            {
                "mcpServers": {
                    "math": {
                        "command": "python",
                        "args": ["add_server.py"],
                    },
                },
            }
        )
        self.assertIsInstance(config, McpConfig)
        self.assertIn("math", config.mcp_servers)
        self.assertEqual(config.mcp_servers["math"].command, "python")

    def test_extra_key_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            McpConfig.model_validate(
                {
                    "mcpServers": {
                        "a": {
                            "command": "echo",
                            "unknown": True,
                        },
                    },
                }
            )

    def test_empty_command_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_mcp_config({"mcpServers": {"a": {"command": "   "}}})

    def test_missing_mcp_servers_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            parse_mcp_config({})


if __name__ == "__main__":
    unittest.main()
