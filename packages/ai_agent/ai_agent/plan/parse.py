from __future__ import annotations

from ai_agent.json_extract import extract_first_json_object
from ai_agent.plan.models import Plan, PlanStep


class PlanParseError(ValueError):
    """规划结果无法解析为合法计划。"""


def parse_plan_text(text: str) -> Plan:
    """
    从模型文本中解析计划 JSON。

    Args:
        text: 模型返回的原始文本

    Returns:
        校验后的计划对象

    Raises:
        PlanParseError: JSON 无效或缺少 steps
    """
    data = extract_first_json_object(text)
    if data is None:
        raise PlanParseError("规划输出不是合法 JSON 对象")
    steps_raw = data.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise PlanParseError("steps 须为非空数组")
    steps: list[PlanStep] = []
    for item in steps_raw:
        if not isinstance(item, dict):
            raise PlanParseError("每个 step 须为对象")
        steps.append(PlanStep.model_validate(item))
    summary = data.get("summary")
    return Plan(
        summary=summary if isinstance(summary, str) else None,
        steps=steps,
    )
