from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .events import (
    ActionCompleted,
    ActionError,
    ActionStarted,
    ConditionChecked,
    EventFired,
    ListenerEvent,
    Loaded,
    LoadError,
    ObserverAfter,
    Started,
    Stopped,
    TriggerAborted,
    TriggerCompleted,
    TriggerError,
    TriggerSkipped,
    TriggerStarted,
)

if TYPE_CHECKING:
    from automation.runtime.context import Context
    from observer.context import ObserverContext


class BaseListener:
    """自动化生命周期与诊断输出。"""

    def handle(self, event: ListenerEvent) -> None:
        """将具体事件分派到对应 ``on_*`` 钩子；子类通常只覆盖需要响应的钩子。"""

        match event:
            case Loaded(ctx):
                self.on_loaded(ctx)
            case Started():
                self.on_started()
            case Stopped():
                self.on_stopped()
            case EventFired(name, data):
                self.on_event_fired(name, data)
            case TriggerStarted(name):
                self.on_trigger_started(name)
            case TriggerSkipped(name):
                self.on_trigger_skipped(name)
            case TriggerCompleted(name, elapsed):
                self.on_trigger_completed(name, elapsed)
            case TriggerAborted(tname, cname):
                self.on_trigger_aborted(tname, cname)
            case TriggerError(name, err):
                self.on_trigger_error(name, err)
            case ConditionChecked(t, c, passed):
                self.on_condition_checked(t, c, passed)
            case ActionStarted(t, a, params):
                self.on_action_started(t, a, params)
            case ActionCompleted(t, a, elapsed, params):
                self.on_action_completed(t, a, elapsed, params)
            case ActionError(t, a, err):
                self.on_action_error(t, a, err)
            case LoadError(section, instance, phase, code, err):
                self.on_load_error(section, instance, phase, code, err)
            case ObserverAfter(obs):
                self.on_observer_after(obs)

    def on_loaded(self, context: Context) -> None:
        pass

    def on_started(self) -> None:
        pass

    def on_stopped(self) -> None:
        pass

    def on_event_fired(self, event_name: str, data: dict[str, Any]) -> None:
        pass

    def on_trigger_started(self, trigger_name: str) -> None:
        pass

    def on_trigger_skipped(self, trigger_name: str) -> None:
        pass

    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None:
        pass

    def on_trigger_aborted(
        self, trigger_name: str, condition_name: str
    ) -> None:
        pass

    def on_trigger_error(self, trigger_name: str, error: Exception) -> None:
        pass

    def on_condition_checked(
        self, trigger_name: str, condition_name: str, passed: bool
    ) -> None:
        pass

    def on_action_started(
        self, trigger_name: str, action_name: str, params: dict | None
    ) -> None:
        pass

    def on_action_completed(
        self,
        trigger_name: str,
        action_name: str,
        elapsed: float,
        params: dict | None,
    ) -> None:
        pass

    def on_action_error(
        self, trigger_name: str, action_name: str, error: Exception
    ) -> None:
        pass

    def on_load_error(
        self,
        section: str,
        instance: str,
        phase: object,
        code: object,
        error: Exception,
    ) -> None:
        pass

    def on_observer_after(self, obs: ObserverContext) -> None:
        pass
