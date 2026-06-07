from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from ai_agent.mcp_debug import McpDebugLog


class McpDebugLogTests(unittest.TestCase):
    def test_log_writes_timestamped_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ai_agent.mcp.debug.log"
            debug = McpDebugLog(path)
            debug.log("load mcp config")
            text = path.read_text(encoding="utf-8")
            self.assertIn("load mcp config", text)

    def test_from_environ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "from_env.log"
            old = os.environ.pop("AI_AGENT_MCP_DEBUG_LOG", None)
            try:
                os.environ["AI_AGENT_MCP_DEBUG_LOG"] = str(path)
                debug = McpDebugLog()
                self.assertTrue(debug.enabled)
                debug.log("via env")
                self.assertIn("via env", path.read_text(encoding="utf-8"))
            finally:
                if old is None:
                    os.environ.pop("AI_AGENT_MCP_DEBUG_LOG", None)
                else:
                    os.environ["AI_AGENT_MCP_DEBUG_LOG"] = old


if __name__ == "__main__":
    unittest.main()
