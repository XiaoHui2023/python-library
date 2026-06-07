from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ai_agent.skill import catalog
from ai_agent.skill.builtin_registry import BuiltinToolRegistry
from ai_agent.skill.catalog import SkillSummary
from ai_agent.skill.frontmatter import split_frontmatter
from ai_agent.skill.models import LoadedSkill, SkillToolDecl
from ai_agent.skill.roots import SkillRootsSandbox, normalize_skill_roots
from ai_agent.context import RunContext
from ai_agent.skill.tool_declarations import parse_tool_declarations
from ai_agent.tools import Tool, ToolRegistry

_SKILL_TOOL_PREFIX = "skill"
_SKILL_ROOT_ALIASES = frozenset({"project", "user", "enable"})


class SkillManager:
    """
    技能动态能力层：扫描目录、按需载入正文与子工具。

    系统提示固定附带技能摘要；模型通过 ``load_skill`` 载入全文。
    单次 ReAct 运行结束后清空已载入正文与子工具。

    Args:
        roots: 技能根目录；可为单路径、路径序列或根键到路径的映射
        builtin_registry: 宿主预注册的内置工具表；未传则新建空表（供测试注入）
    """

    def __init__(
        self,
        roots: Mapping[str, Path | str] | Sequence[Path | str] | Path | str,
        *,
        builtin_registry: BuiltinToolRegistry | None = None,
    ) -> None:
        mapping = normalize_skill_roots(roots)
        self._sandbox = SkillRootsSandbox(mapping)
        self._prefix = _SKILL_TOOL_PREFIX
        self._builtin = builtin_registry or BuiltinToolRegistry()
        self._registry: ToolRegistry | None = None
        self._available: dict[str, SkillSummary] = {}
        self._loaded: dict[str, LoadedSkill] = {}
        self._enabled: set[str] = set()
        self._skill_tools: dict[str, list[Tool]] = {}
        self._run: RunContext | None = None
        self._run_enabled_refs: set[str] = set()
        self._run_context_refs: set[str] = set()
        self.refresh()

    @property
    def root_keys(self) -> tuple[str, ...]:
        """已配置的根键名。"""
        return self._sandbox.root_keys

    @property
    def enabled_skill_refs(self) -> tuple[str, ...]:
        """当前已载入的 skill 引用。"""
        return tuple(sorted(self._enabled))

    @property
    def run_context_skill_refs(self) -> tuple[str, ...]:
        """当前 ReAct 运行内已注入上下文的 skill 引用。"""
        return tuple(sorted(self._run_context_refs))

    @property
    def builtin_registry(self) -> BuiltinToolRegistry:
        """内置工具注册表，供宿主扩展。"""
        return self._builtin

    def bind_registry(self, registry: ToolRegistry) -> None:
        """绑定会话级工具表；变更载入状态后须 ``sync_to_registry``。"""
        self._registry = registry

    def sync_to_registry(self) -> None:
        """按当前状态刷新工具表中的管理与 skill 子工具层。"""
        if self._registry is None:
            return
        self._registry.set_management_tools(self.build_management_tools())
        self._registry.set_skill_tools(self.build_enabled_tools())

    def begin_run(self, run: RunContext) -> None:
        """
        标记新一轮 ReAct 开始；运行内载入的 skill 在 ``end_run`` 时还原。

        Args:
            run: 当前 ``RunContext``
        """
        self._run = run
        self._run_enabled_refs = set()
        self._run_context_refs = set()
        run.ephemeral_skill_context = ""

    def end_run(self) -> None:
        """结束当前 ReAct 运行：清空临时 skill 上下文并卸载本运行内载入的 skill。"""
        if self._run is not None:
            self._run.ephemeral_skill_context = ""
        for ref in list(self._run_enabled_refs):
            self._disable_unlocked(ref)
        self._run = None
        self._run_enabled_refs = set()
        self._run_context_refs = set()
        self.sync_to_registry()

    def refresh(self) -> str:
        """
        重新扫描 skill 根目录，并移除已不存在 skill 的载入状态。

        Returns:
            扫描结果摘要
        """
        summaries = catalog.scan_skills(self._sandbox)
        self._available = {item.skill_ref: item for item in summaries}
        stale = [ref for ref in self._enabled if ref not in self._available]
        for ref in stale:
            self._disable_unlocked(ref)
        self._loaded = {
            ref: loaded
            for ref, loaded in self._loaded.items()
            if ref in self._available
        }
        return catalog.format_skill_list(summaries)

    def format_catalog_for_prompt(self) -> str:
        """生成须拼入系统提示的技能目录块。"""
        items = sorted(self._available.values(), key=lambda item: item.skill_ref)
        return catalog.format_skill_catalog_prompt(items)

    def load_skill(self, skill_ref: str) -> str:
        """
        载入 skill 全文；若有子工具则一并注册，并注入当前 ReAct 运行上下文。

        Args:
            skill_ref: ``{root_key}/{skill_id}``
        """
        ref = self._normalize_ref(skill_ref)
        if ref in self._run_context_refs:
            return f"skill 已在当前运行上下文中: {ref}"
        self._require_available(ref)
        loaded = self._load(ref)
        tools = self._build_skill_tools(ref, loaded.tool_decls)
        self._skill_tools[ref] = tools
        self._enabled.add(ref)
        if self._run is not None:
            self._run_enabled_refs.add(ref)
            self._run_context_refs.add(ref)
            self._append_run_skill_context(ref, loaded.text)
        names = ", ".join(tool.name for tool in tools) if tools else "（无子工具）"
        context_note = "；正文已注入本轮上下文" if self._run is not None else ""
        return f"已载入 {ref}；子工具: {names}{context_note}"

    def enable_skill(self, skill_ref: str) -> str:
        """``load_skill`` 的兼容别名。"""
        return self.load_skill(skill_ref)

    def disable_skill(self, skill_ref: str) -> str:
        """
        卸载 skill 并移除其子工具与本轮临时上下文。

        Args:
            skill_ref: ``{root_key}/{skill_id}``
        """
        ref = self._normalize_ref(skill_ref)
        if ref not in self._enabled:
            return f"skill 未载入: {ref}"
        self._disable_unlocked(ref)
        self._run_context_refs.discard(ref)
        if self._run is not None:
            self._rebuild_run_skill_context()
        return f"已卸载 {ref}"

    def build_management_tools(self) -> list[Tool]:
        """生成 skill 管理工具（不含已载入 skill 的子工具）。"""
        specs = self._management_specs()
        return [
            Tool(
                name=self._tool_name(short),
                description=description,
                parameters=parameters,
                handler=self._wrap_sync(handler) if sync_after else handler,
            )
            for short, description, parameters, handler, _writable_only, sync_after in specs
        ]

    def build_enabled_tools(self) -> list[Tool]:
        """合并当前已载入 skill 暴露的全部子工具。"""
        tools: list[Tool] = []
        for ref in sorted(self._enabled):
            tools.extend(self._skill_tools.get(ref, ()))
        return tools

    def build_all_flat_tools(self) -> list[Tool]:
        """管理工具与已载入子工具合并（兼容旧版 ``SkillKit.build_tools``）。"""
        return self.build_management_tools() + self.build_enabled_tools()

    def _management_specs(
        self,
    ) -> list[
        tuple[str, str, dict[str, Any], Callable[..., Any], bool, bool]
    ]:
        return [
            (
                "load_skill",
                "载入指定 skill 的全文到本轮上下文；若 skill 声明子工具则一并注册。"
                "路径格式 {root_key}/{skill_id}，如 skills/chat-search-answer。",
                {
                    "type": "object",
                    "properties": {
                        "skill_ref": {
                            "type": "string",
                            "description": "格式 {root_key}/{skill_id}",
                        },
                    },
                    "required": ["skill_ref"],
                    "additionalProperties": False,
                },
                self.load_skill,
                False,
                True,
            ),
            (
                "disable_skill",
                "卸载指定 skill，移除其子工具与本轮临时上下文。",
                {
                    "type": "object",
                    "properties": {
                        "skill_ref": {
                            "type": "string",
                            "description": "格式 {root_key}/{skill_id}",
                        },
                    },
                    "required": ["skill_ref"],
                    "additionalProperties": False,
                },
                self.disable_skill,
                False,
                True,
            ),
            (
                "refresh_skills",
                "重新扫描 skill 根目录；系统提示中的技能目录在下一轮对话更新。",
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                self.refresh,
                False,
                True,
            ),
        ]

    def _wrap_sync(self, handler: Callable[..., Any]) -> Callable[..., Any]:
        def wrapped(**kwargs: Any) -> Any:
            result = handler(**kwargs)
            self.sync_to_registry()
            return result

        return wrapped

    def _tool_name(self, short: str) -> str:
        return f"{self._prefix}__{short}"

    def _skill_tool_name(self, skill_ref: str, decl_name: str) -> str:
        safe_ref = skill_ref.replace("/", "_")
        return f"{self._prefix}__{safe_ref}__{decl_name}"

    def _build_skill_tools(
        self,
        skill_ref: str,
        decls: tuple[SkillToolDecl, ...],
    ) -> list[Tool]:
        tools: list[Tool] = []
        seen: set[str] = set()
        for decl in decls:
            api_name = self._skill_tool_name(skill_ref, decl.name)
            if api_name in seen:
                raise ValueError(f"{skill_ref} 内工具名重复: {decl.name}")
            seen.add(api_name)
            for other_ref, other_tools in self._skill_tools.items():
                if other_ref == skill_ref:
                    continue
                if any(tool.name == api_name for tool in other_tools):
                    raise ValueError(f"工具名已被其他 skill 占用: {api_name}")
            resolved = self._builtin.resolve(decl.handler)
            if resolved is None:
                raise ValueError(
                    f"{skill_ref} 的 {decl.name} 引用未知 handler: {decl.handler}"
                )
            tools.append(
                Tool(
                    name=api_name,
                    description=resolved.description,
                    parameters=resolved.parameters,
                    handler=resolved.handler,
                )
            )
        return tools

    def _load(self, skill_ref: str) -> LoadedSkill:
        ref = self._normalize_ref(skill_ref)
        cached = self._loaded.get(ref)
        if cached is not None:
            return cached
        self._require_available(ref)
        text = catalog.load_skill_text(self._sandbox, ref)
        meta, body = split_frontmatter(text)
        summary = self._available[ref]
        decls = tuple(parse_tool_declarations(text))
        loaded = LoadedSkill(
            summary=summary,
            text=text,
            meta=meta,
            body=body,
            tool_decls=decls,
        )
        self._loaded[ref] = loaded
        return loaded

    def _disable_unlocked(self, skill_ref: str) -> None:
        self._enabled.discard(skill_ref)
        self._skill_tools.pop(skill_ref, None)
        self._run_enabled_refs.discard(skill_ref)

    def _append_run_skill_context(self, skill_ref: str, text: str) -> None:
        if self._run is None:
            return
        block = f"## 技能 {skill_ref}\n\n{text.strip()}"
        existing = self._run.ephemeral_skill_context.strip()
        if existing:
            self._run.ephemeral_skill_context = f"{existing}\n\n{block}"
        else:
            self._run.ephemeral_skill_context = block

    def _rebuild_run_skill_context(self) -> None:
        if self._run is None:
            return
        parts: list[str] = []
        for ref in sorted(self._run_context_refs):
            loaded = self._loaded.get(ref)
            if loaded is None:
                loaded = self._load(ref)
            parts.append(f"## 技能 {ref}\n\n{loaded.text.strip()}")
        self._run.ephemeral_skill_context = "\n\n".join(parts)

    def _require_available(self, skill_ref: str) -> None:
        if skill_ref not in self._available:
            raise ValueError(f"未找到 skill: {skill_ref}")

    def _normalize_ref(self, skill_ref: str) -> str:
        cleaned = skill_ref.strip().strip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise ValueError(f"skill_ref 非法: {skill_ref!r}")
        cleaned = self._apply_skill_root_alias(cleaned)
        self._sandbox.parse_ref(cleaned)
        return cleaned

    def _apply_skill_root_alias(self, skill_ref: str) -> str:
        parts = skill_ref.split("/")
        if len(parts) != 2:
            return skill_ref
        root_key, skill_id = parts[0], parts[1]
        if root_key in self._sandbox.root_keys:
            return skill_ref
        if root_key in _SKILL_ROOT_ALIASES and "skills" in self._sandbox.root_keys:
            return f"skills/{skill_id}"
        return skill_ref
