from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from examples._support.example_env import load_dotenv_file


@dataclass(frozen=True)
class LlmConfig:
    """示例用：LLM 连接参数（勿放入 ai_agent 库）。"""

    api_key: str
    model: str
    base_url: str
    temperature: float | None = None
    max_tokens: int | None = None
    thinking_enabled: bool = False


def load_llm_config_from_env_map(env: Mapping[str, str]) -> LlmConfig:
    """
    从键值映射读取 LLM_*。

    Raises:
        ValueError: 缺少必填项或数值格式无效
    """
    api_key = env.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise ValueError("缺少 LLM_API_KEY，请在示例目录 .env 中配置")

    model = env.get("LLM_MODEL", "").strip()
    if not model:
        raise ValueError("缺少 LLM_MODEL，请在示例目录 .env 中配置")

    base_url = env.get("LLM_BASE_URL", "").strip()
    if not base_url:
        raise ValueError("缺少 LLM_BASE_URL，请在示例目录 .env 中配置")

    temperature: float | None = None
    raw_temp = env.get("LLM_TEMPERATURE", "").strip()
    if raw_temp:
        try:
            temperature = float(raw_temp)
        except ValueError as exc:
            raise ValueError("LLM_TEMPERATURE 须为浮点数") from exc

    max_tokens: int | None = None
    raw_max = env.get("LLM_MAX_TOKENS", "").strip()
    if raw_max:
        try:
            max_tokens = int(raw_max)
        except ValueError as exc:
            raise ValueError("LLM_MAX_TOKENS 须为整数") from exc

    thinking_enabled = False
    raw_thinking = env.get("LLM_THINKING_ENABLED", "").strip().lower()
    if raw_thinking in ("1", "true", "yes", "on"):
        thinking_enabled = True
    elif raw_thinking in ("0", "false", "no", "off", ""):
        thinking_enabled = False
    elif raw_thinking:
        raise ValueError(
            "LLM_THINKING_ENABLED 须为 true/false（或 1/0、yes/no、on/off）",
        )

    return LlmConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        thinking_enabled=thinking_enabled,
    )


def load_llm_config(example_dir: Path) -> LlmConfig:
    """
    从示例目录下的 ``.env`` 读取 LLM 配置（不修改 ``os.environ``）。

    Args:
        example_dir: 含 ``.env`` 的示例根目录（如 ``examples/chat``）
    """
    env_path = example_dir / ".env"
    return load_llm_config_from_env_map(load_dotenv_file(env_path))
