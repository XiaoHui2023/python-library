from __future__ import annotations

from pathlib import Path
from datetime import datetime

from .base import BaseListener
from .record import TriggerRecord, ActionRecord, ConditionRecord


class TraceListener(BaseListener):
    """将每次触发的执行记录写入独立 JSON 文件，用于调试回溯"""

    def __init__(self, output_dir: str | Path):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, TriggerRecord] = {}

    def on_trigger_started(self, trigger_name: str) -> None:
        self._pending[trigger_name] = TriggerRecord(trigger=trigger_name)

    def on_condition_checked(self, trigger_name: str, condition_name: str, passed: bool) -> None:
        if record := self._pending.get(trigger_name):
            record.conditions.append(ConditionRecord(expr=condition_name, passed=passed))

    def on_action_started(self, trigger_name: str, action_name: str, *, params: dict | None = None) -> None:
        if record := self._pending.get(trigger_name):
            record.actions.append(ActionRecord(action=action_name, params=params))

    def on_action_completed(self, trigger_name: str, action_name: str, elapsed: float, *, params: dict | None = None) -> None:
        if record := self._pending.get(trigger_name):
            if record.actions and record.actions[-1].action == action_name:
                record.actions[-1].status = "completed"
                record.actions[-1].elapsed = round(elapsed, 4)

    def on_action_error(self, trigger_name: str, action_name: str, error: Exception) -> None:
        if record := self._pending.get(trigger_name):
            if record.actions and record.actions[-1].action == action_name:
                record.actions[-1].status = "error"
                record.actions[-1].error = str(error)

    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None:
        self._flush(trigger_name, "completed", elapsed)

    def on_trigger_error(self, trigger_name: str, error: Exception) -> None:
        if record := self._pending.get(trigger_name):
            record.error = str(error)
        self._flush(trigger_name, "error")

    def on_trigger_aborted(self, trigger_name: str, condition_name: str) -> None:
        if record := self._pending.get(trigger_name):
            record.aborted_by = condition_name
        self._flush(trigger_name, "aborted")

    def _flush(self, trigger_name: str, status: str, elapsed: float | None = None) -> None:
        record = self._pending.pop(trigger_name, None)
        if record is None:
            return
        record.status = status
        record.finished_at = datetime.now()
        if elapsed is not None:
            record.elapsed = round(elapsed, 4)

        now = datetime.now()
        trigger_dir = self._output_dir / now.strftime("%Y-%m-%d") / trigger_name
        trigger_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{now.strftime('%H-%M-%S-%f')}.json"
        (trigger_dir / filename).write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )