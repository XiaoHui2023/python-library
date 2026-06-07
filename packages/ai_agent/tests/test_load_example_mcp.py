from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from examples._support.llm_config import load_llm_config_from_env_map
from examples._support.load_example_mcp import load_example_mcp_json


class TestLoadExampleMcpJson(unittest.TestCase):
    def test_load_example_mcp_json(self) -> None:
        document = {
            "mcpServers": {
                "demo": {"command": "python", "args": []},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            example_dir = Path(tmp)
            (example_dir / "mcp.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            loaded = load_example_mcp_json(example_dir)
        self.assertIn("demo", loaded["mcpServers"])

    def test_rejects_agent_env(self) -> None:
        document = {
            "agentEnv": {"LLM_API_KEY": "k"},
            "mcpServers": {"demo": {"command": "python", "args": []}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            example_dir = Path(tmp)
            (example_dir / "mcp.json").write_text(
                json.dumps(document),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_example_mcp_json(example_dir)

    def test_load_llm_config_from_env_map(self) -> None:
        cfg = load_llm_config_from_env_map(
            {
                "LLM_API_KEY": "key",
                "LLM_BASE_URL": "https://api.example.com/v1",
                "LLM_MODEL": "gpt-test",
                "LLM_TEMPERATURE": "0.5",
            },
        )
        self.assertEqual(cfg.api_key, "key")
        self.assertEqual(cfg.temperature, 0.5)


if __name__ == "__main__":
    unittest.main()
