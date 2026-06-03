from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class PlanStep(BaseModel):
    """计划中的单步，按顺序串行执行。"""

    id: str = Field(description="步骤唯一标识，如 step-1")
    title: str = Field(description="短标题")
    objective: str = Field(description="本步须完成的目标")
    optional: bool = Field(default=False, description="执行时可由模型判定跳过")
    hint_tools: list[str] = Field(default_factory=list, description="建议使用的工具名")

    @field_validator("hint_tools", mode="before")
    @classmethod
    def _hint_tools_none_as_empty(cls, value: object) -> object:
        if value is None:
            return []
        return value

    required_tool: str | None = Field(
        default=None,
        description="本步应调用的工具名；仅作规划提示，执行阶段不强制",
    )


class Plan(BaseModel):
    """串行多步计划。"""

    steps: list[PlanStep] = Field(min_length=1, description="按执行顺序排列")
    summary: str | None = Field(default=None, description="规划说明，可选")


class PlanRunResult(BaseModel):
    """一次 run_with_plan 的完整结果。"""

    plan: Plan
    step_outputs: dict[str, str] = Field(description="步骤 id 到该步完整输出")
    final_output: str = Field(description="返回给用户的最终文本")
    skipped_step_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="执行时判定跳过的可选步 id",
    )
