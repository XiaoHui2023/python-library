from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from examples._support.llm_config import load_llm_config_from_env_map
from examples._support.mcp_json_config import (
    load_mcp_json_document,
    mcp_servers_payload,
)


class McpJsonConfigTests(unittest.TestCase):
    def test_mcp_servers_payload(self) -> None:
        document = {
            "mcpServers": {
                "demo": {"command": "python", "args": [], "env": {"BOCHA_API_KEY": "b"}},
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            loaded = load_mcp_json_document(path)
        payload = mcp_servers_payload(loaded)
        self.assertIn("demo", payload["mcpServers"])

    def test_rejects_agent_env(self) -> None:
        document = {
            "agentEnv": {"LLM_API_KEY": "k"},
            "mcpServers": {"demo": {"command": "python", "args": []}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_mcp_json_document(path)

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
