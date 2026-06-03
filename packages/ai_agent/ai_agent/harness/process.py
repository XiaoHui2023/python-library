from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_DEFAULT_TIMEOUT = 120
_MAX_TIMEOUT = 600
_MAX_OUTPUT_CHARS = 100_000


def clamp_timeout(timeout_seconds: int) -> int:
    if timeout_seconds <= 0:
        return _DEFAULT_TIMEOUT
    return min(timeout_seconds, _MAX_TIMEOUT)


def format_process_result(
    *,
    exit_code: int,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
) -> str:
    parts: list[str] = []
    if timed_out:
        parts.append("状态: 超时")
    else:
        parts.append(f"退出码: {exit_code}")
    if stdout:
        parts.append("--- stdout ---")
        parts.append(stdout)
    if stderr:
        parts.append("--- stderr ---")
        parts.append(stderr)
    text = "\n".join(parts)
    if len(text) > _MAX_OUTPUT_CHARS:
        overflow = len(text) - _MAX_OUTPUT_CHARS
        text = text[:_MAX_OUTPUT_CHARS] + f"\n...（输出已截断，省略 {overflow} 字符）"
    return text


def run_shell(
    command: str,
    *,
    work_dir: Path,
    timeout_seconds: int = 0,
) -> str:
    command = command.strip()
    if not command:
        raise ValueError("command 不能为空")
    timeout = clamp_timeout(timeout_seconds)
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return format_process_result(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
    return format_process_result(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_python(
    code: str,
    *,
    work_dir: Path,
    timeout_seconds: int = 0,
) -> str:
    code = code.strip()
    if not code:
        raise ValueError("code 不能为空")
    timeout = clamp_timeout(timeout_seconds)
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return format_process_result(
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
    return format_process_result(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
