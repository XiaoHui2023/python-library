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


class SkillManager:
    """
    技能动态能力层：扫描、加载、启用与停用，并向工具表注入管理与子工具。

    启用技能时加载全文并暴露子工具；单次对话运行内正文可拼入临时系统上下文，
    运行结束后恢复。技能仓库运行时只读，不可通过工具改写磁盘文件。

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
        self._plan_active = False
        self._plan_delivery_refs: tuple[str, ...] = ()
        self.refresh()

    @property
    def root_keys(self) -> tuple[str, ...]:
        """已配置的根键名。"""
        return self._sandbox.root_keys

    @property
    def enabled_skill_refs(self) -> tuple[str, ...]:
        """当前已启用的 skill 引用。"""
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
        """绑定会话级工具表；变更启用状态后须 ``sync_to_registry``。"""
        self._registry = registry

    def sync_to_registry(self) -> None:
        """按当前状态刷新工具表中的管理与 skill 子工具层。"""
        if self._registry is None:
            return
        self._registry.set_management_tools(self.build_management_tools())
        self._registry.set_skill_tools(self.build_enabled_tools())

    def begin_plan(self) -> None:
        """标记一次 ``PlanRunner.run`` 开始；与 ``end_plan`` 成对调用。"""
        self._plan_active = True
        self._plan_delivery_refs = ()

    def end_plan(self) -> None:
        """结束计划作用域并停用计划期间仍挂起的 skill。"""
        self._plan_active = False
        self._plan_delivery_refs = ()
        for ref in list(self._enabled):
            self._disable_unlocked(ref)
        self.sync_to_registry()

    def set_plan_delivery_skills(self, refs: tuple[str, ...]) -> None:
        """
        指定下一步 ReAct 开始前预载入上下文的终稿 skill。

        仅在 ``begin_plan`` 之后、下一步 ``begin_run`` 之前调用；非终稿步传空元组。
        """
        if not self._plan_active:
            return
        self._plan_delivery_refs = refs

    def begin_run(self, run: RunContext) -> None:
        """
        标记新一轮 ReAct 开始；运行内启用的 skill 在 ``end_run`` 时还原。

        Args:
            run: 当前 ``RunContext``
        """
        self._run = run
        self._run_enabled_refs = set()
        self._run_context_refs = set()
        run.ephemeral_skill_context = ""
        if self._plan_active and self._plan_delivery_refs:
            for ref in self._plan_delivery_refs:
                self._activate_skill_for_run(ref)

    def end_run(self) -> None:
        """结束当前 ReAct 运行：清空临时 skill 上下文并停用本运行内启用的 skill。"""
        if self._run is not None:
            self._run.ephemeral_skill_context = ""
        for ref in list(self._run_enabled_refs):
            self._disable_unlocked(ref)
        self._run = None
        self._run_enabled_refs = set()
        self._run_context_refs = set()
        self._plan_delivery_refs = ()
        self.sync_to_registry()

    def refresh(self) -> str:
        """
        重新扫描 skill 根目录，并移除已不存在 skill 的启用状态。

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

    def list_skills(self, root_key: str = "") -> str:
        """
        列出可用 skill 摘要。

        Args:
            root_key: 仅扫描该根；留空扫描全部
        """
        if root_key.strip():
            key = self._sandbox.require_root(root_key)
            items = [
                item for item in self._available.values() if item.root_key == key
            ]
        else:
            items = list(self._available.values())
        items.sort(key=lambda item: item.skill_ref)
        lines = [catalog.format_skill_list(items)]
        if self._enabled:
            lines.append("")
            lines.append("已启用: " + ", ".join(sorted(self._enabled)))
        return "\n".join(lines)

    def get_metadata(self, skill_ref: str) -> str:
        """读取 frontmatter 元数据摘要。"""
        loaded = self._load(skill_ref)
        meta = loaded.meta
        if not meta:
            return f"{skill_ref}：无 frontmatter"
        out = [f"{skill_ref} 元数据："]
        for key in sorted(meta.keys()):
            out.append(f"  {key}: {meta[key]}")
        if loaded.tool_decls:
            out.append("  tools:")
            for decl in loaded.tool_decls:
                out.append(f"    - {decl.name} ({decl.handler})")
        return "\n".join(out)

    def enable_skill(self, skill_ref: str) -> str:
        """
        启用 skill：加载全文、注册子工具，并在当前 ReAct 运行内注入临时上下文。

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
        return f"已启用 {ref}；子工具: {names}{context_note}"

    def disable_skill(self, skill_ref: str) -> str:
        """
        停用 skill 并移除其子工具。

        Args:
            skill_ref: ``{root_key}/{skill_id}``
        """
        ref = self._normalize_ref(skill_ref)
        if ref not in self._enabled:
            return f"skill 未启用: {ref}"
        self._disable_unlocked(ref)
        self._run_context_refs.discard(ref)
        if self._run is not None:
            self._rebuild_run_skill_context()
        return f"已停用 {ref}"

    def roots_info(self) -> str:
        """说明 skill 根目录约束。"""
        keys = ", ".join(self._sandbox.root_keys)
        lines = [
            f"已配置 skill 根: {keys}。",
            "引用格式为 {root_key}/{skill_id}；",
            "仅可访问各根下技能子目录中的文件，无法越出根目录。",
            "使用 list_skills 扫描；enable_skill 启用后暴露子工具并注入本轮上下文。",
            "skill 仓库在运行时只读，须在开发阶段维护文件。",
        ]
        return "".join(lines)

    def build_management_tools(self) -> list[Tool]:
        """生成 skill 管理工具（不含已启用 skill 的子工具）。"""
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
        """合并当前已启用 skill 暴露的全部子工具。"""
        tools: list[Tool] = []
        for ref in sorted(self._enabled):
            tools.extend(self._skill_tools.get(ref, ()))
        return tools

    def build_all_flat_tools(self) -> list[Tool]:
        """管理工具与已启用子工具合并（兼容旧版 ``SkillKit.build_tools``）。"""
        return self.build_management_tools() + self.build_enabled_tools()

    def _management_specs(
        self,
    ) -> list[
        tuple[str, str, dict[str, Any], Callable[..., Any], bool, bool]
    ]:
        return [
            (
                "list_skills",
                "扫描已配置的 skill 根目录，列出技能及启用状态。",
                {
                    "type": "object",
                    "properties": {
                        "root_key": {
                            "type": "string",
                            "description": "仅扫描该根键；留空扫描全部根",
                        },
                    },
                    "additionalProperties": False,
                },
                self.list_skills,
                False,
                False,
            ),
            (
                "enable_skill",
                "启用指定 skill，使其声明的子工具加入当前会话工具表。",
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
                self.enable_skill,
                False,
                True,
            ),
            (
                "disable_skill",
                "停用指定 skill 并移除其子工具与本轮临时上下文。",
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
                "重新扫描 skill 根目录并同步可用列表。",
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                self.refresh,
                False,
                True,
            ),
            (
                "get_metadata",
                "读取指定 skill 的 SKILL.md frontmatter 元数据。",
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
                self.get_metadata,
                False,
                False,
            ),
            (
                "roots_info",
                "查看 skill 根目录的使用约束与已配置的根键。",
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                self.roots_info,
                False,
                False,
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

    def _activate_skill_for_run(self, skill_ref: str) -> None:
        """为当前 ReAct 运行启用 skill 并注入正文（计划终稿步预载，不经工具调用）。"""
        ref = self._normalize_ref(skill_ref)
        if ref in self._run_context_refs:
            return
        self._require_available(ref)
        loaded = self._load(ref)
        tools = self._build_skill_tools(ref, loaded.tool_decls)
        self._skill_tools[ref] = tools
        self._enabled.add(ref)
        if self._run is not None:
            self._run_enabled_refs.add(ref)
            self._run_context_refs.add(ref)
            self._append_run_skill_context(ref, loaded.text)
        self.sync_to_registry()

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
        self._sandbox.parse_ref(cleaned)
        return cleaned
