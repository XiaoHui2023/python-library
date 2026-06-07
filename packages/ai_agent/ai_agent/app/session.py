from __future__ import annotations



from collections.abc import Iterable, Mapping, Sequence

from pathlib import Path

from typing import Any



from ai_agent.agent import Agent

from ai_agent.context import ChatMessage

from ai_agent.harness import Harness

from ai_agent.listener import AgentListener, normalize_listeners

from ai_agent.memory import MemorySystem

from ai_agent.skill import SkillKit

from ai_agent.skill.manager import SkillManager

from ai_agent.tools import Tool, ToolRegistry





class AgentSession:
    """
    单会话入口：独立工作区、沙箱工具、对话代理与可选分层记忆。

    由 AgentApp.open_session 组装；应用代码勿直接构造。

    Args:
        session_id: 会话标识，对应总沙箱下该会话子目录名
        workspace: 会话根目录（含 harness、memory 等固定子目录）
        harness: 已绑定工作区的沙箱与可选技能套件
        agent: 已注册工具表与规则的语言模型代理
        skill_manager: 技能动态管理器；未配置技能根时为 None
        memory: 分层记忆；未配置记忆模型时为 None
    """

    def __init__(
        self,
        *,
        session_id: str,
        workspace: Path,
        harness: Harness,
        agent: Agent,
        skill_manager: SkillManager | None = None,
        memory: MemorySystem | None = None,
    ) -> None:

        self._session_id = session_id

        self._workspace = workspace

        self._harness = harness

        self._agent = agent

        self._skill_manager = skill_manager

        self._memory = memory

        self._messages: list[ChatMessage] = []



    @property

    def memory(self) -> MemorySystem | None:

        """绑定的分层记忆；未配置时为 None。"""

        return self._memory



    @property

    def session_id(self) -> str:

        """会话标识。"""

        return self._session_id



    @property

    def workspace(self) -> Path:

        """该会话在总沙箱下的根目录（含 harness、memory 等子目录）。"""

        return self._workspace



    @property

    def harness(self) -> Harness:

        """已安装隔离工作区与 skill 的 Harness。"""

        return self._harness



    @property

    def skill_manager(self) -> SkillManager | None:

        """本会话的 skill 能力管理器；未配置 skill_roots 时为 None。"""

        return self._skill_manager



    @property

    def agent(self) -> Agent:

        """绑定了本会话分层工具表的 ReAct 代理。"""

        return self._agent



    @property

    def messages(self) -> tuple[ChatMessage, ...]:

        """当前对话历史（只读视图）。"""

        return tuple(self._messages)



    def clear_messages(self) -> None:

        """清空本会话对话历史。"""

        self._messages.clear()

    def replace_messages(self, messages: Sequence[ChatMessage]) -> None:
        """
        用给定列表替换内存中的对话历史（不写入磁盘）。

        Args:
            messages: 新的消息序列
        """
        self._messages.clear()
        self._messages.extend(messages)



    def load_skill(self, skill_ref: str) -> str:
        """
        载入 skill 全文并刷新工具表。

        Args:
            skill_ref: ``{root_key}/{skill_id}``
        """
        manager = self._require_skill_manager()
        message = manager.load_skill(skill_ref)
        manager.sync_to_registry()
        return message



    def disable_skill(self, skill_ref: str) -> str:

        """

        停用 skill 并刷新工具表。



        Args:

            skill_ref: ``{root_key}/{skill_id}``

        """

        manager = self._require_skill_manager()

        message = manager.disable_skill(skill_ref)

        manager.sync_to_registry()

        return message



    def refresh_skills(self) -> str:

        """

        重新扫描 skill 根并刷新工具表。



        Returns:

            扫描结果摘要

        """

        manager = self._require_skill_manager()

        message = manager.refresh()

        manager.sync_to_registry()

        return message



    def effective_tools(self) -> list[Tool]:

        """当前传入模型的全部工具实例。"""

        return self._agent.context.tools.effective_tools()



    async def run(

        self,

        *,

        user_message: str,

        speaker: str = "user",

    ) -> str:

        """

        追加用户消息后运行一轮 ReAct，并将助手回复写入历史。



        Args:

            user_message: 本轮用户输入

            speaker: 用户讲述者显示名，多用户场景下区分身份



        Returns:

            助手最终文本

        """

        full_system = self.build_system_prompt()

        if self._memory is not None:

            self._memory.append(

                speaker=speaker,

                role="user",

                content=user_message,

            )

            merged_system, messages = self._memory.context_for_agent(

                system_prompt=full_system,

            )

        else:

            name = speaker if speaker != "user" else None

            self._messages.append(

                ChatMessage(role="user", content=user_message, name=name),

            )

            merged_system = full_system

            messages = list(self._messages)



        output = await self._agent.run_with_system(

            system_prompt=merged_system,

            messages=messages,

        )



        if self._memory is not None:

            self._memory.append(

                speaker="assistant",

                role="assistant",

                content=output,

            )

        else:

            self._messages.append(ChatMessage(role="assistant", content=output))

        return output



    def build_system_prompt(self) -> str:
        """
        由规则与技能目录拼成的系统提示（skill 正文在载入后注入单次运行上下文）。

        Returns:
            无内容时为空字符串
        """
        parts: list[str] = []
        rules_block = self._agent.rules.build_system_prompt()
        if rules_block:
            parts.append(rules_block)
        if self._skill_manager is not None:
            catalog_block = self._skill_manager.format_catalog_for_prompt()
            if catalog_block:
                parts.append(catalog_block)
        return "\n\n".join(parts)



    def _require_skill_manager(self) -> SkillManager:

        if self._skill_manager is None:

            raise ValueError("本会话未配置 skill_roots")

        return self._skill_manager





def build_session(

    *,

    session_id: str,

    workspace: Path,

    harness_workspace: Path,

    skill_roots: (

        Mapping[str, Path | str] | Sequence[Path | str] | Path | str | None

    ),

    rule_paths: Sequence[Path | str] | None,

    api_key: str,

    model: str,

    base_url: str,

    temperature: float | None,

    max_tokens: int | None,

    thinking_enabled: bool = False,

    max_steps: int,

    extra_tools: list[Tool],

    listeners: list[AgentListener],

    memory: MemorySystem | None = None,

    harness_enabled: bool = False,


) -> AgentSession:
    """
    组装单会话的沙箱、分层工具表与对话代理。

    Args:
        session_id: 会话标识
        workspace: 会话根目录
        harness_workspace: 沙箱读写工作区目录（一般为会话下 harness 子目录）
        skill_roots: 技能仓库根；未配置则不挂载技能
        rule_paths: 系统规则文件路径列表
        api_key: 语言模型 API 密钥
        model: 模型名
        base_url: API 地址
        temperature: 采样温度
        max_tokens: 单次补全 token 上限
        thinking_enabled: 是否在请求中开启思考模式
        max_steps: ReAct 最大步数
        extra_tools: 额外工具列表（如 MCP）
        listeners: 运行时监听列表
        memory: 已构造的分层记忆；未传则为 None
        harness_enabled: 为 False 时不向模型注册 Harness 沙箱工具
    Returns:
        可运行的 AgentSession
    """

    skill_manager: SkillManager | None = None

    skill_kit: SkillKit | None = None

    if skill_roots is not None:

        skill_kit = SkillKit(skill_roots)

        skill_manager = skill_kit.manager

    harness_kwargs: dict[str, Any] = {}

    if skill_kit is not None:

        harness_kwargs["skill_kit"] = skill_kit

    harness = Harness(harness_workspace, **harness_kwargs)

    registry = ToolRegistry()

    base_tools: list = []
    if harness_enabled:
        base_tools = harness.build_tools()
    registry.set_base_tools(base_tools)

    if skill_manager is not None:

        skill_manager.bind_registry(registry)

        skill_manager.sync_to_registry()

    if extra_tools:

        registry.set_extra_tools(extra_tools)

    agent = Agent(

        api_key=api_key,

        model=model,

        base_url=base_url,

        temperature=temperature,

        max_tokens=max_tokens,

        thinking_enabled=thinking_enabled,

        tools=registry,

        rule_paths=rule_paths,

        max_steps=max_steps,

        listeners=listeners,

    )

    if skill_manager is not None:

        def on_run_begin(run: RunContext) -> None:
            skill_manager.begin_run(run)

        def on_run_end(_run: RunContext) -> None:
            skill_manager.end_run()

        agent.context.on_run_begin = on_run_begin
        agent.context.on_run_end = on_run_end

    return AgentSession(

        session_id=session_id,

        workspace=workspace,

        harness=harness,

        agent=agent,

        skill_manager=skill_manager,

        memory=memory,

    )





def normalize_session_listeners(

    listeners: AgentListener | Iterable[AgentListener] | None,

) -> list[AgentListener]:

    return normalize_listeners(listeners)

