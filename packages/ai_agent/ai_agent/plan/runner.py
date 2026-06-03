from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Sequence

from ai_agent.app.output_format import (
    run_output_instruction,
    step_intermediate_instruction,
)
from ai_agent.context import ChatMessage, RunPhase, RunPhaseKind
from ai_agent.listener import (
    AgentListener,
    notify_plan_ready,
    notify_plan_start,
    notify_plan_step_end,
    notify_plan_step_start,
)
from ai_agent.llm import LLMClient
from ai_agent.plan.models import Plan, PlanRunResult, PlanStep
from ai_agent.plan.planner import PlanPlanner
from ai_agent.plan.delivery import (
    delivery_skill_refs_for_step,
    plan_delivery_preload_note,
)

if TYPE_CHECKING:
    from ai_agent.app.session import AgentSession

SKIP_STEP_MARKER = "SKIP_STEP"


class PlanStepFailedError(RuntimeError):
    """某必做步骤未产生有效输出时抛出。"""


class PlanRunner:
    """
    编排规划与逐步执行：先 ``PlanPlanner``，再对每步调用会话上的 ReAct。

    步间上下文携带已完成步骤的完整 output；可选步由执行模型自行判定是否跳过。
    """

    def __init__(
        self,
        llm: LLMClient,
        *,
        listeners: Sequence[AgentListener] | None = None,
    ) -> None:
        self._planner = PlanPlanner(llm)
        self._listeners: list[AgentListener] = list(listeners or [])

    async def run(
        self,
        session: AgentSession,
        *,
        user_message: str,
        speaker: str = "user",
        extra_planning_context: str = "",
    ) -> PlanRunResult:
        """
        规划并串行执行各步，返回最终回答。

        Args:
            session: 已装配 Harness 与工具的会话
            user_message: 用户输入
            speaker: 多用户场景下的讲述者名
            extra_planning_context: 拼入规划阶段的附加说明

        Returns:
            计划、各步完整输出与最终文本

        Raises:
            PlanStepFailedError: 必做步骤无有效输出
        """
        full_system = session.build_system_prompt()
        planning_messages, merged_system = session._prepare_plan_run(
            user_message=user_message,
            system_prompt=full_system,
            speaker=speaker,
        )
        await notify_plan_start(self._listeners)
        plan = await self._planner.plan(
            user_message=user_message,
            business_system_prompt=merged_system,
            messages=planning_messages,
            extra_planning_context=extra_planning_context,
            listeners=self._listeners,
        )
        await notify_plan_ready(self._listeners, plan)
        skill_manager = session.skill_manager
        if skill_manager is not None:
            skill_manager.begin_plan()
        try:
            step_outputs: dict[str, str] = {}
            skipped: list[str] = []
            for index, step in enumerate(plan.steps):
                await notify_plan_step_start(
                    self._listeners,
                    step_index=index,
                    step=step,
                    plan=plan,
                )
                output = await self._run_step(
                    session,
                    base_system=full_system,
                    plan=plan,
                    step=step,
                    step_index=index,
                    user_message=user_message,
                    prior_outputs=step_outputs,
                )
                skipped_step = step.optional and _is_skip_output(output)
                if skipped_step:
                    skipped.append(step.id)
                elif not output.strip() and not step.optional:
                    raise PlanStepFailedError(
                        f"步骤 {step.id}（{step.title}）未产生输出"
                    )
                else:
                    step_outputs[step.id] = output
                await notify_plan_step_end(
                    self._listeners,
                    step_index=index,
                    step=step,
                    plan=plan,
                    output=output,
                    skipped=skipped_step,
                )
                if skipped_step:
                    continue
            final = _pick_final_output(plan, step_outputs, skipped)
            session._finish_plan_run(
                user_message=user_message,
                final_output=final,
                speaker=speaker,
            )
            return PlanRunResult(
                plan=plan,
                step_outputs=step_outputs,
                final_output=final,
                skipped_step_ids=tuple(skipped),
            )
        finally:
            if skill_manager is not None:
                skill_manager.end_plan()

    async def _run_step(
        self,
        session: AgentSession,
        *,
        base_system: str,
        plan: Plan,
        step: PlanStep,
        step_index: int,
        user_message: str,
        prior_outputs: dict[str, str],
    ) -> str:
        is_last_step = step_index + 1 >= len(plan.steps)
        delivery_refs: tuple[str, ...] = ()
        preloaded_delivery = False
        skill_manager = session.skill_manager
        if skill_manager is not None:
            if is_last_step:
                delivery_refs = delivery_skill_refs_for_step(step)
                skill_manager.set_plan_delivery_skills(delivery_refs)
                preloaded_delivery = bool(delivery_refs)
            else:
                skill_manager.set_plan_delivery_skills(())
        step_system = _build_step_system(
            base_system,
            plan=plan,
            step=step,
            step_index=step_index,
            prior_outputs=prior_outputs,
            is_last_step=is_last_step,
            preloaded_delivery=preloaded_delivery,
            delivery_skill_refs=delivery_refs,
        )
        step_user = _build_step_user(
            user_message=user_message,
            step=step,
            step_index=step_index,
            total=len(plan.steps),
            is_last_step=is_last_step,
            preloaded_delivery=preloaded_delivery,
        )
        return await session.run_with_messages(
            messages=[ChatMessage(role="user", content=step_user)],
            system_prompt=step_system,
            phase=RunPhase(
                kind=RunPhaseKind.STEP,
                step_index=step_index,
                step_id=step.id,
            ),
        )


def _is_skip_output(text: str) -> bool:
    stripped = text.strip()
    return stripped == SKIP_STEP_MARKER or stripped.startswith(f"{SKIP_STEP_MARKER}\n")


def _pick_final_output(
    plan: Plan,
    step_outputs: dict[str, str],
    skipped: list[str],
) -> str:
    skipped_set = set(skipped)
    for step in reversed(plan.steps):
        if step.id in skipped_set:
            continue
        out = step_outputs.get(step.id, "").strip()
        if out:
            return out
    return ""


def _build_step_system(
    base_system: str,
    *,
    plan: Plan,
    step: PlanStep,
    step_index: int,
    prior_outputs: dict[str, str],
    is_last_step: bool,
    preloaded_delivery: bool = False,
    delivery_skill_refs: tuple[str, ...] = (),
) -> str:
    lines = [base_system.rstrip(), "", "## 当前计划摘要"]
    if plan.summary:
        lines.append(plan.summary.strip())
    lines.append(f"共 {len(plan.steps)} 步，当前为第 {step_index + 1} 步。")
    if prior_outputs:
        lines.append("")
        lines.append("## 已完成步骤的完整输出")
        for sid, out in prior_outputs.items():
            lines.append(f"### {sid}")
            lines.append(out)
    lines.append("")
    lines.append("## 本步任务")
    lines.append(f"**{step.title}**")
    lines.append(step.objective.strip())
    if step.hint_tools:
        lines.append(f"建议工具：{', '.join(step.hint_tools)}")
    if step.required_tool and not preloaded_delivery:
        lines.append(f"若需要请使用工具：{step.required_tool}")
    if preloaded_delivery and delivery_skill_refs:
        joined = ", ".join(delivery_skill_refs)
        lines.append(f"终稿改写技能已预载：{joined}；勿再调用 enable_skill。")
    if step.optional:
        lines.append(
            f"本步为可选。若前述输出已足以回答用户，请仅回复 {SKIP_STEP_MARKER}，"
            "不要调用工具。"
        )
    if not is_last_step:
        lines.append("本步为中间步骤：勿按最终交付 JSON 格式回复用户。")
    return "\n".join(lines)


def _build_step_user(
    *,
    user_message: str,
    step: PlanStep,
    step_index: int,
    total: int,
    is_last_step: bool,
    preloaded_delivery: bool = False,
) -> str:
    parts = [
        f"用户原始请求：{user_message.strip()}",
        "",
        f"请完成计划第 {step_index + 1}/{total} 步：{step.title}",
    ]
    if is_last_step:
        parts.extend(["", run_output_instruction()])
        if preloaded_delivery:
            parts.extend(["", plan_delivery_preload_note()])
    else:
        parts.extend(["", step_intermediate_instruction()])
    return "\n\n".join(parts)
