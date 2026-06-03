from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values


def load_dotenv_file(env_path: Path) -> dict[str, str]:
    """
    读取示例目录下的 ``.env``（不写入当前进程的 ``os.environ``）。

    Raises:
        ValueError: 文件不存在
    """
    if not env_path.is_file():
        raise ValueError(
            f"缺少 {env_path}，请复制同目录 .env.example 为 .env 并填写",
        )
    raw = dotenv_values(env_path)
    return {str(key): str(value) for key, value in raw.items() if value is not None and key}
