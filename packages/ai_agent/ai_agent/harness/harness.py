from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ai_agent.harness.process import run_python, run_shell
from ai_agent.harness.sandbox import HarnessSandbox
from ai_agent.skill.manager import SkillManager
from ai_agent.skill.skill_kit import SkillKit
from ai_agent.tools import Tool

_HARNESS_TOOL_PREFIX = "harness"


class Harness:
    """
    隔离工作区上的文件与进程能力；与对话代理核分离，由调用方构造后导出为工具列表。

    路径均相对工作区根；可挂载只读技能区。工具说明与返回值不向模型暴露宿主机绝对路径。

    Args:
        workspace: 沙箱工作区根目录
        skill_roots: 只读技能仓库根；与 skill_kit 二选一
        skill_kit: 已构造的 SkillKit；与 skill_roots 二选一
    """

    def __init__(
        self,
        workspace: Path | str,
        *,
        skill_roots: (
            Mapping[str, Path | str] | Sequence[Path | str] | Path | str | None
        ) = None,
        skill_kit: SkillKit | None = None,
    ) -> None:
        if skill_kit is not None and skill_roots is not None:
            raise ValueError("skill_kit 与 skill_roots 不可同时指定")
        self._sandbox = HarnessSandbox(Path(workspace))
        self._prefix = _HARNESS_TOOL_PREFIX
        self._skill_kit: SkillKit | None = None
        if skill_kit is not None:
            self._skill_kit = skill_kit
        elif skill_roots is not None:
            self._skill_kit = SkillKit(skill_roots)

    @property
    def workspace(self) -> Path:
        """沙箱工作区根目录（供应用侧配置与测试使用，勿写入模型可见文案）。"""
        return self._sandbox.root

    @property
    def skill(self) -> SkillKit:
        """已配置的 SkillKit；未配置 skill_roots 时访问会报错。"""
        if self._skill_kit is None:
            raise ValueError("未配置 skill_roots")
        return self._skill_kit

    def _tool_name(self, short: str) -> str:
        return f"{self._prefix}__{short}"

    def read_file(self, path: str, offset: int = 1, limit: int = 0) -> str:
        """
        读取工作区内文本文件。

        Args:
            path: 相对工作区根的路径
            offset: 起始行号，从 1 起
            limit: 最多读取行数；0 表示读到末尾
        """
        return self._sandbox.read_text_file(path, offset=offset, limit=limit)

    def write_file(self, path: str, content: str, append: bool = False) -> str:
        """
        写入或追加工作区内文本文件。

        Args:
            path: 相对工作区根的路径
            content: 文件内容
            append: 为 True 时追加
        """
        return self._sandbox.write_text_file(path, content, append=append)

    def list_files(
        self,
        path: str = "",
        max_entries: int = 200,
        pattern: str = "",
    ) -> str:
        """
        扫描工作区内文件与目录。

        Args:
            path: 相对工作区根的子目录；留空则扫描整个工作区
            max_entries: 最多返回条数
            pattern: 可选 glob，如 *.py
        """
        entries = self._sandbox.list_entries(
            path,
            max_entries=max_entries,
            pattern=pattern,
        )
        if not entries:
            return "（空）"
        truncated = len(entries) >= max_entries
        lines = "\n".join(entries)
        if truncated:
            lines += f"\n...（已达上限 {max_entries} 条）"
        return lines

    def run_shell(self, command: str, cwd: str = "", timeout_seconds: int = 0) -> str:
        """
        在工作区内执行 shell 命令。

        Args:
            command: shell 命令
            cwd: 相对工作区的子目录；留空则用工作区根
            timeout_seconds: 超时秒数；0 则用默认
        """
        work_dir = (
            self._sandbox.root
            if not cwd.strip()
            else self._sandbox.resolve_path(cwd)
        )
        if not work_dir.is_dir():
            raise ValueError(f"cwd 不是目录: {cwd or '.'}")
        return run_shell(
            command,
            work_dir=work_dir,
            timeout_seconds=timeout_seconds,
        )

    def run_python(self, code: str, timeout_seconds: int = 0) -> str:
        """
        在工作区根目录下执行 Python 代码片段。

        Args:
            code: Python 源码
            timeout_seconds: 超时秒数；0 则用默认
        """
        return run_python(
            code,
            work_dir=self._sandbox.root,
            timeout_seconds=timeout_seconds,
        )

    def workspace_info(self) -> str:
        """说明隔离工作区约束（不包含宿主机绝对路径）。"""
        return (
            "隔离工作区已启用。所有路径均相对于工作区根；"
            "无法读取或写入工作区外的文件。"
            "使用 list_files 查看目录结构。"
        )

    def build_skill_tools(self) -> list[Tool]:
        """生成 skill 管理 Tool 列表；须已配置 skill_roots。"""
        return self.skill.build_management_tools()

    def build_all_tools(self) -> list[Tool]:
        """合并沙箱、skill 管理与已启用子工具（未配置 skill_roots 时仅沙箱）。"""
        tools = self.build_tools()
        if self._skill_kit is not None:
            tools = tools + self._skill_kit.build_all_flat_tools()
        return tools

    @property
    def skill_manager(self) -> SkillManager:
        """已配置的 SkillManager；未配置 skill_roots 时访问会报错。"""
        return self.skill.manager

    def build_tools(self) -> list[Tool]:
        """生成沙箱区 Tool 列表。"""
        specs: list[tuple[str, str, dict[str, Any], Any]] = [
            (
                "read_file",
                "读取隔离工作区内文本文件，返回带行号的内容。",
                {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的文件路径",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "起始行号，从 1 起，默认 1",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最多读取行数；0 表示读到末尾",
                        },
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
                self.read_file,
            ),
            (
                "write_file",
                "写入或追加隔离工作区内文本文件，必要时创建父目录。",
                {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的文件路径",
                        },
                        "content": {"type": "string", "description": "要写入的文本"},
                        "append": {
                            "type": "boolean",
                            "description": "为 true 时追加，否则覆盖",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
                self.write_file,
            ),
            (
                "list_files",
                "扫描隔离工作区内的文件与目录，仅返回相对路径。",
                {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "相对工作区根的子目录；留空扫描整个工作区",
                        },
                        "max_entries": {
                            "type": "integer",
                            "description": "最多返回条数，默认 200",
                        },
                        "pattern": {
                            "type": "string",
                            "description": "可选 glob，如 *.txt",
                        },
                    },
                    "additionalProperties": False,
                },
                self.list_files,
            ),
            (
                "run_shell",
                "在隔离工作区内执行 shell 命令，返回退出码与标准输出/错误。",
                {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "shell 命令"},
                        "cwd": {
                            "type": "string",
                            "description": "相对工作区的子目录；留空则用工作区根",
                        },
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "超时秒数，默认 120，上限 600",
                        },
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
                self.run_shell,
            ),
            (
                "run_python",
                "在隔离工作区根目录下执行 Python 代码片段。",
                {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python 源码"},
                        "timeout_seconds": {
                            "type": "integer",
                            "description": "超时秒数，默认 120，上限 600",
                        },
                    },
                    "required": ["code"],
                    "additionalProperties": False,
                },
                self.run_python,
            ),
            (
                "workspace_info",
                "查看隔离工作区的使用约束。",
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                self.workspace_info,
            ),
        ]
        return [
            Tool(
                name=self._tool_name(short),
                description=description,
                parameters=parameters,
                handler=handler,
            )
            for short, description, parameters, handler in specs
        ]
