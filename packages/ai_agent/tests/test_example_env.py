from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples._support.example_env import load_dotenv_file
from examples._support.llm_config import load_llm_config


class ExampleEnvTests(unittest.TestCase):
    def test_load_dotenv_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "LLM_API_KEY=secret\nLLM_BASE_URL=https://api.example.com/v1\n"
                "LLM_MODEL=gpt-test\n",
                encoding="utf-8",
            )
            env = load_dotenv_file(env_path)
        self.assertEqual(env["LLM_API_KEY"], "secret")

    def test_load_llm_config_from_example_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "LLM_API_KEY=key\nLLM_BASE_URL=https://api.example.com/v1\n"
                "LLM_MODEL=m\n",
                encoding="utf-8",
            )
            cfg = load_llm_config(root)
        self.assertEqual(cfg.model, "m")


if __name__ == "__main__":
    unittest.main()
