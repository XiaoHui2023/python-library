from __future__ import annotations

from collections.abc import Sequence

from ai_agent.context import ChatMessage, RunPhase, RunPhaseKind
from ai_agent.harness.prompts import PLANNING_SYSTEM_PROMPT
from ai_agent.listener import AgentListener
from ai_agent.llm import LLMClient
from ai_agent.plan.complete import complete_text
from ai_agent.plan.models import Plan
from ai_agent.plan.parse import PlanParseError, parse_plan_text




class PlanPlanner:

    """

    规划入口：用与执行相同的语言模型产出串行计划，不调用工具。



    规划与执行共用 ``LLMClient``，由 ``PlanRunner`` 或测试注入。

    """



    def __init__(self, llm: LLMClient) -> None:

        self._llm = llm

        self._planning_system_prompt = PLANNING_SYSTEM_PROMPT.strip()



    async def plan(
        self,
        *,
        user_message: str,
        business_system_prompt: str,
        messages: list[ChatMessage],
        extra_planning_context: str = "",
        listeners: Sequence[AgentListener] | None = None,
    ) -> Plan:

        """

        根据用户请求与对话历史生成计划。



        Args:

            user_message: 本轮用户输入（已可能在 messages 末尾）

            business_system_prompt: 业务系统提示（含规则与技能等自然语言说明）

            messages: 送入规划的历史（通常含本轮用户消息）

            extra_planning_context: 附加说明（如附件摘要）



        Returns:

            解析后的串行计划



        Raises:

            PlanParseError: 模型输出无法解析且重试后仍失败

        """

        system = _build_planning_system(

            self._planning_system_prompt,

            business_system_prompt,

            extra_planning_context,

        )

        history = _history_without_last_user(messages, user_message)

        user_block = _format_planning_user(user_message, business_system_prompt)

        last_error: PlanParseError | None = None

        for attempt in range(2):

            text = await complete_text(
                self._llm,
                system_prompt=system,
                user_content=user_block
                if attempt == 0
                else f"{user_block}\n\n上次输出无法解析，请仅输出合法 JSON 对象。",
                history=history,
                listeners=listeners,
                phase=RunPhase(kind=RunPhaseKind.PLANNING),
                parse_from_answer_text_only=True,
            )

            try:

                return parse_plan_text(text)

            except PlanParseError as exc:

                last_error = exc

                continue

        assert last_error is not None

        raise last_error





def _history_without_last_user(

    messages: list[ChatMessage],

    user_message: str,

) -> list[ChatMessage]:

    if not messages:

        return []

    last = messages[-1]

    if last.role == "user" and last.content.strip() == user_message.strip():

        return list(messages[:-1])

    return list(messages)





def _format_planning_user(user_message: str, business_system_prompt: str) -> str:

    lines = [

        "## 用户请求",

        user_message.strip(),

        "",

        "## 业务系统提示（供规划参考，含规则与技能）",

        business_system_prompt.strip() or "(无)",

        "",

        "请结合上文规则与技能说明分解步骤，输出 JSON 计划。",

    ]

    return "\n".join(lines)





def _build_planning_system(

    planning_base: str,

    business_system_prompt: str,

    extra_planning_context: str,

) -> str:

    parts = [planning_base]

    if business_system_prompt.strip():

        parts.append("")

        parts.append("## 业务背景")

        parts.append(business_system_prompt.strip())

    if extra_planning_context.strip():

        parts.append("")

        parts.append(extra_planning_context.strip())

    return "\n\n".join(parts)


