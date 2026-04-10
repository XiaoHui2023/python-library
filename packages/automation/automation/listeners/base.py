from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from automation.hub import Hub

class BaseListener:
    """自动化生命周期监听器"""

    def on_loaded(self, hub: Hub) -> None: pass
    def on_start(self) -> None: pass
    def on_stop(self) -> None: pass
    def on_event_fired(self, event_name: str) -> None: pass
    def on_trigger_started(self, trigger_name: str) -> None: pass
    def on_trigger_skipped(self, trigger_name: str) -> None: pass
    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None: pass
    def on_trigger_aborted(self, trigger_name: str, condition_name: str) -> None: pass
    def on_trigger_error(self, trigger_name: str, error: Exception) -> None: pass
    def on_condition_checked(self, trigger_name: str, condition_name: str, passed: bool) -> None: pass
    def on_action_started(self, trigger_name: str, action_name: str, *, params: dict | None = None) -> None: pass
    def on_action_completed(self, trigger_name: str, action_name: str, elapsed: float, *, params: dict | None = None) -> None: pass
    def on_action_error(self, trigger_name: str, action_name: str, error: Exception) -> None: pass