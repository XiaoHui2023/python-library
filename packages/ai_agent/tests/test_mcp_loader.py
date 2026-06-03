from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from ai_agent.mcp_loader import _stdio_env


class StdioEnvTests(unittest.TestCase):
    def test_does_not_inherit_parent_environ(self) -> None:
        with patch.dict(os.environ, {"BOCHA_API_KEY": "from-parent"}, clear=False):
            env = _stdio_env(None)
        self.assertNotIn("BOCHA_API_KEY", env)

    def test_server_env_only(self) -> None:
        env = _stdio_env({"BOCHA_API_KEY": "from-config"})
        self.assertEqual(env["BOCHA_API_KEY"], "from-config")


if __name__ == "__main__":
    unittest.main()
