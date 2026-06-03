from __future__ import annotations

from ai_agent.plan.models import Plan, PlanStep


def format_plan_for_terminal(plan: Plan) -> str:
    """
    将计划格式化为终端可读的固定版式文本。

    Args:
        plan: 规划结果

    Returns:
        多行字符串，不含首尾空行
    """
    lines: list[str] = ["--- plan ---"]
    if plan.summary and plan.summary.strip():
        lines.append(f"摘要: {plan.summary.strip()}")
    total = len(plan.steps)
    lines.append(f"步骤（共 {total} 步）:")
    for index, step in enumerate(plan.steps, start=1):
        lines.extend(_format_step_lines(index, step))
    return "\n".join(lines)


def _format_step_lines(index: int, step: PlanStep) -> list[str]:
    optional_tag = "（可选）" if step.optional else ""
    head = f"  {index}. {step.id} · {step.title}{optional_tag}"
    body: list[str] = [head]
    objective = step.objective.strip()
    if objective:
        for line in objective.splitlines():
            body.append(f"     目标: {line}")
    tools_line = _format_tools_line(step)
    if tools_line:
        body.append(f"     {tools_line}")
    return body


def _format_tools_line(step: PlanStep) -> str:
    parts: list[str] = []
    if step.hint_tools:
        parts.append(f"建议工具: {', '.join(step.hint_tools)}")
    if step.required_tool:
        parts.append(f"须用工具: {step.required_tool}")
    return "；".join(parts)
