from __future__ import annotations
from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ConditionRecord(BaseModel):
    expr: str
    passed: bool


class ActionRecord(BaseModel):
    action: str
    params: dict | None = None
    status: Literal["running", "completed", "error"] = "running"
    elapsed: float | None = None
    error: str | None = None


class TriggerRecord(BaseModel):
    trigger: str
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: datetime | None = None
    status: Literal["running", "completed", "error", "aborted"] = "running"
    elapsed: float | None = None
    error: str | None = None
    aborted_by: str | None = None
    conditions: list[ConditionRecord] = Field(default_factory=list)
    actions: list[ActionRecord] = Field(default_factory=list)