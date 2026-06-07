from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ai_agent.json_extract import extract_first_json_object


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
