from __future__ import annotations

import re

from ai_agent.plan.models import PlanStep

_SKILL_REF_PATTERN = re.compile(r"\b[\w-]+/[\w-]+(?:/[\w-]+)*\b")
_ENABLE_TOOL_NAMES = frozenset({"enable_skill", "skill__enable_skill"})
_DELIVERY_SKILL_ALIASES: tuple[tuple[str, str], ...] = (
    ("skills/chat-search-answer", "skills/chat-search-answer"),
    ("chat-search-answer", "skills/chat-search-answer"),
    ("聊天搜索回答", "skills/chat-search-answer"),
)

_PLAN_DELIVERY_PRELOAD_NOTE = (
    "改写技能已载入本步系统上下文，无需再调用 enable_skill，"
    "直接按技能正文原则交付终稿。"
)


def delivery_skill_refs_for_step(step: PlanStep) -> tuple[str, ...]:
    """
    从计划步 objective / title 解析终稿改写 skill 引用。

    匹配 ``{root_key}/{skill_id}`` 形式（如 ``skills/chat-search-answer``）。
    """
    text = f"{step.title}\n{step.objective}"
    refs: list[str] = []
    for match in _SKILL_REF_PATTERN.finditer(text):
        candidate = match.group(0)
        if candidate not in refs and "/" in candidate:
            refs.append(candidate)
    for needle, ref in _DELIVERY_SKILL_ALIASES:
        if needle in text and ref not in refs:
            refs.append(ref)
    return tuple(refs)


def plan_delivery_preload_note() -> str:
    """终稿步已预载 skill 时拼入用户消息的说明。"""
    return _PLAN_DELIVERY_PRELOAD_NOTE
