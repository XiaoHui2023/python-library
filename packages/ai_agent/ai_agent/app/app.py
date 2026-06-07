from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ai_agent.app._workspace import (
    SESSION_MEMORY_SUBDIR,
    reset_session_subdirs,
    resolve_app_sandbox_root,
    session_harness_workspace,
    session_workspace,
    validate_session_id,
)
from ai_agent.app.harness_io import (
    compose_user_message_with_attachments,
    format_input_files_context,
    resolve_output_files,
    stage_input_files,
)
from ai_agent.app.output_format import parse_structured_run_output
from ai_agent.app.packet import RunInputPacket, RunOutputPacket
from ai_agent.app.session_store import (
    clear_conversation,
    load_conversation,
    save_conversation,
)
from ai_agent.app.session import (
    AgentSession,
    build_session,
    normalize_session_listeners,
)
from ai_agent.listener import AgentListener, notify_app_run_end
from ai_agent.memory import MemoryConfig, MemorySystem
from ai_agent.tools import Tool


class AgentApp:
    """
    多会话应用入口：在总沙箱下按会话标识分配子目录，并装配隔离工作区、技能与对话代理。

    各会话下固定 harness 子目录供工具读写、memory 子目录供分层记忆；语言模型与记忆压缩
    模型在 AgentApp 构造时配置一次，会话间工作区与对话历史相互隔离。

    Args:
        sandbox: 总沙箱根目录
        skill_roots: 只读技能仓库根；键为根键，值为目录路径；未配置则不挂载技能
        rule_paths: 系统规则文本文件路径列表，固定拼入各轮系统提示
        api_key: 主对话语言模型 API 密钥
        model: 主对话模型名
        base_url: 主对话 API 地址
        temperature: 主对话采样温度；未设则由服务端默认
        max_tokens: 主对话单次补全 token 上限；未设则由服务端默认
        thinking_enabled: 主对话是否向兼容接口开启思考模式（``enable_thinking``）
        max_steps: 单轮 ReAct 最大步数
        extra_tools: 各会话共用的额外工具（如 MCP），共享同一列表引用
        listeners: 运行时事件监听；可传单个或序列
        memory_api_key: 记忆压缩用模型 API 密钥；三者缺一则不启用记忆
        memory_model: 记忆压缩用模型名
        memory_base_url: 记忆压缩用 API 地址
        memory_short_term_max_messages: 短期记忆条数上限
        memory_short_term_overflow_batch: 每次从短期弹出的条数
        memory_date_memory_days: 日期记忆保留天数
        memory_date_memory_max_entries_per_day: 单日日期记忆条目上限
        memory_long_term_max_chunks: 长期记忆块数上限
        memory_important_max_entries: 重要记忆条目上限
        harness_enabled: 是否向模型注册 Harness 沙箱工具；默认关闭
    """

    def __init__(
        self,
        sandbox: Path | str,
        *,
        skill_roots: (
            Mapping[str, Path | str]
            | Sequence[Path | str]
            | Path
            | str
            | None
        ) = None,
        rule_paths: Sequence[Path | str] | None = None,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking_enabled: bool = False,
        max_steps: int = 20,
        extra_tools: list[Tool] | None = None,
        listeners: AgentListener | Iterable[AgentListener] | None = None,
        memory_api_key: str | None = None,
        memory_model: str | None = None,
        memory_base_url: str | None = None,
        memory_short_term_max_messages: int = 20,
        memory_short_term_overflow_batch: int = 5,
        memory_date_memory_days: int = 7,
        memory_date_memory_max_entries_per_day: int = 50,
        memory_long_term_max_chunks: int = 30,
        memory_important_max_entries: int = 20,
        harness_enabled: bool = False,
    ) -> None:
        self._sandbox_root = resolve_app_sandbox_root(sandbox)
        self._skill_roots = skill_roots
        self._rule_paths = tuple(rule_paths) if rule_paths else None
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._thinking_enabled = thinking_enabled
        self._max_steps = max_steps
        self._shared_extra_tools: list[Tool] = list(extra_tools or [])
        self._listeners = normalize_session_listeners(listeners)
        self._memory_api_key = memory_api_key
        self._memory_model = memory_model
        self._memory_base_url = memory_base_url
        self._memory_config = MemoryConfig(
            short_term_max_messages=memory_short_term_max_messages,
            short_term_overflow_batch=memory_short_term_overflow_batch,
            date_memory_days=memory_date_memory_days,
            date_memory_max_entries_per_day=memory_date_memory_max_entries_per_day,
            long_term_max_chunks=memory_long_term_max_chunks,
            important_max_entries=memory_important_max_entries,
        )
        self._harness_enabled = harness_enabled
        self._sessions: dict[str, AgentSession] = {}

    @property
    def shared_extra_tools(self) -> list[Tool]:
        """各会话共用的已加载工具（如 MCP），运行时共享同一列表引用。"""
        return self._shared_extra_tools

    def set_shared_extra_tools(self, tools: list[Tool]) -> None:
        """
        替换各会话共用的工具表（须在 ``run`` 之前完成，例如 MCP ``load`` 之后）。

        Args:
            tools: 新工具列表；会替换内部列表内容
        """
        self._shared_extra_tools.clear()
        self._shared_extra_tools.extend(tools)

    @property
    def sandbox_root(self) -> Path:
        """总沙箱根目录。"""
        return self._sandbox_root

    @property
    def harness_enabled(self) -> bool:
        """各会话是否向模型注册 Harness 沙箱工具。"""
        return self._harness_enabled

    @property
    def thinking_enabled(self) -> bool:
        """主对话是否在请求中开启思考模式。"""
        return self._thinking_enabled

    def list_session_ids(self) -> tuple[str, ...]:
        """当前已打开（在内存中）的会话 id。"""
        return tuple(sorted(self._sessions))

    def has_session(self, session_id: str) -> bool:
        """是否已有该会话实例。"""
        label = validate_session_id(session_id)
        return label in self._sessions

    def get_session(self, session_id: str) -> AgentSession | None:
        """
        获取已打开的会话。

        Args:
            session_id: 会话 id

        Returns:
            已存在则返回会话，否则 ``None``
        """
        label = validate_session_id(session_id)
        return self._sessions.get(label)

    def open_session(
        self,
        session_id: str,
        *,
        memory: MemorySystem | None = None,
    ) -> AgentSession:
        """
        打开或复用一会话：分配子沙箱并安装 Harness 与 Agent。

        Args:
            session_id: 会话 id；重复打开返回同一 ``AgentSession`` 实例
            memory: 外部已构造的记忆系统；未传且 AgentApp 已配置记忆模型时自动创建

        Returns:
            该会话实例
        """
        label = validate_session_id(session_id)
        existing = self._sessions.get(label)
        if existing is not None:
            return existing
        session_root = session_workspace(self._sandbox_root, label)
        harness_workspace = session_harness_workspace(session_root)
        session_memory = memory
        if session_memory is None:
            session_memory = self._build_default_memory(session_root)
        session = build_session(
            session_id=label,
            workspace=session_root,
            harness_workspace=harness_workspace,
            skill_roots=self._skill_roots,
            rule_paths=self._rule_paths,
            api_key=self._api_key,
            model=self._model,
            base_url=self._base_url,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            thinking_enabled=self._thinking_enabled,
            max_steps=self._max_steps,
            extra_tools=self._shared_extra_tools,
            listeners=self._listeners,
            memory=session_memory,
            harness_enabled=self._harness_enabled,
        )
        self._sessions[label] = session
        return session

    async def run(self, packet: RunInputPacket) -> RunOutputPacket:
        """
        运行入口：接收输入数据包，执行单轮 ReAct 后返回输出数据包。

        单次调用内打开会话、处理完毕后从内存移除会话实例；Harness 与对话状态落在
        ``sessions/<session_id>/``。运行时事件通过构造时传入的 ``listeners`` 回调。

        Args:
            packet: 用户名、会话 id、要求、附件路径与是否清空会话状态等

        Returns:
            结构化回答与须交还用户的文件路径列表
        """
        label = validate_session_id(packet.session_id)
        user_name = packet.user_name.strip()
        if not user_name:
            raise ValueError("user_name 不能为空")
        session_root = session_workspace(self._sandbox_root, label)
        if packet.clear:
            reset_session_subdirs(session_root)
            clear_conversation(session_root)
        self.close_session(label)
        session = self.open_session(label)
        try:
            if not packet.clear and session.memory is None:
                session.replace_messages(load_conversation(session_root))
            input_files = packet.input_files if self._harness_enabled else ()
            staged = stage_input_files(input_files, session.harness.workspace)
            file_context = format_input_files_context(staged)
            user_message = compose_user_message_with_attachments(
                packet.request,
                staged,
                file_context,
            )
            final_text = await session.run(
                user_message=user_message,
                speaker=user_name,
            )
            answer, rel_files = parse_structured_run_output(final_text)
            output_files = resolve_output_files(rel_files, session.harness.workspace)
            if session.memory is None:
                save_conversation(session_root, list(session.messages))
            packet = RunOutputPacket(
                user_name=user_name,
                session_id=label,
                answer=answer,
                output_files=output_files,
            )
            await notify_app_run_end(self._listeners, packet)
            return packet
        finally:
            self.close_session(label)

    def _build_default_memory(self, workspace: Path) -> MemorySystem | None:
        key = self._memory_api_key
        model = self._memory_model
        base = self._memory_base_url
        if not key or not model or not base:
            return None
        storage = workspace / SESSION_MEMORY_SUBDIR
        return MemorySystem(
            storage,
            api_key=key,
            model=model,
            base_url=base,
            config=self._memory_config,
        )

    def close_session(self, session_id: str) -> bool:
        """
        从应用中移除会话实例（不删除磁盘上的子沙箱内容）。

        Args:
            session_id: 会话 id

        Returns:
            若原先存在并已移除则为 True
        """
        label = validate_session_id(session_id)
        return self._sessions.pop(label, None) is not None
