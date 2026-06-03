from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ai_agent.json_extract import extract_first_json_object

_RUN_OUTPUT_INSTRUCTION = """
## 最终交付格式（最后一步必须遵守）
完成全部计划步骤后，你的**最终可见回复**必须是**仅含一个 JSON 对象**的文本，不要 Markdown 围栏，不要其它说明。字段：
- ``answer``：面向用户的完整回答（字符串）
- ``output_files``：需要交还给用户的文件路径数组，路径**相对 Harness 工作区根**（如 ``incoming/foo.xlsx``、``out/result.csv``）；无文件则 ``[]``

格式硬性要求：
- 整段输出必须是**合法 JSON**（可用单行，或仅在字符串内使用 ``\\n`` 表示换行）；``answer`` 内勿写入未转义的真实换行。
- ``answer`` 字符串值内勿使用未转义的 ASCII 双引号（``"``）；须转义为 ``\\"`` 或改写为不含英文双引号的表述。
- 除 JSON 外不要任何前后缀文字。
""".strip()


def run_output_instruction() -> str:
    """返回须拼入计划最后一步用户消息末尾的交付格式说明。"""
    return _RUN_OUTPUT_INSTRUCTION


_STEP_INTERMEDIATE_INSTRUCTION = """
## 本步产出要求
本步不是计划的最后一步：勿输出最终交付用的 ``answer`` / ``output_files`` JSON。
首行须写：``会话当前日期：YYYY-MM-DD（来源：builtin__current_time）``（本步已调用该工具时；日期取自工具返回）；首行前勿加 ``---`` 或其它前缀。
其后用简洁中文记录本步**结论要点**（检索时间窗口、事实、条目），供后续步骤使用；条数贴近用户所要的条数，勿堆砌窗口外月份背景。
本步各回合可见回复均用中文；勿写搜索重试过程、搜前搜后寒暄、「再搜一次」「进入下一步」等过程叙述；需要再搜时直接调用工具，勿先发文说明。
同回合**禁止**与 ``builtin__current_time``（或 ``harness__current_time``）一并发起 ``bocha_search`` 等其它工具：须先单独一轮取时，待返回后再搜；并行发起时运行层只执行取时，搜索须下回合重写 query。
若本步无可写产出可只回复「本步已完成」（已取时时仍保留首行日期行）。
""".strip()


def step_intermediate_instruction() -> str:
    """返回拼入非最后计划步用户消息的产出说明。"""
    return _STEP_INTERMEDIATE_INSTRUCTION


class _StructuredRunBody(BaseModel):
    answer: str = Field(description="面向用户的回答")
    output_files: list[str] = Field(default_factory=list)


def parse_structured_run_output(text: str) -> tuple[str, tuple[str, ...]]:
    """
    从模型最终文本解析结构化回答与输出文件列表。

    Args:
        text: 模型原始输出

    Returns:
        回答正文与相对 Harness 的文件路径元组；无法解析 JSON 时整段作为 answer
    """
    stripped = text.strip()
    if not stripped:
        return "", ()
    payload = _extract_json_object(stripped)
    if payload is None:
        return stripped, ()
    try:
        body = _StructuredRunBody.model_validate(payload)
    except ValidationError:
        return stripped, ()
    files = tuple(
        p.strip()
        for p in body.output_files
        if isinstance(p, str) and p.strip()
    )
    return body.answer.strip() or stripped, files


def _extract_json_object(text: str) -> dict[str, Any] | None:
    return extract_first_json_object(text)
