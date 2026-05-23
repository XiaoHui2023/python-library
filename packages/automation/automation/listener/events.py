from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from automation.errors import LoadErrorCode, LoadPhase
from observer.context import ObserverContext

if TYPE_CHECKING:
    from automation.runtime.context import Context


@dataclass(frozen=True)
class Loaded:
    """配置已成功加载并激活。"""

    context: "Context"


@dataclass(frozen=True)
class Started:
    """运行时已开始。"""


@dataclass(frozen=True)
class Stopped:
    """运行时已停止。"""


@dataclass(frozen=True)
class EventFired:
    """某事件已通过条件检查并即将执行回调。"""

    event_name: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TriggerStarted:
    """触发器开始执行动作链。"""

    trigger_name: str


@dataclass(frozen=True)
class TriggerSkipped:
    """触发器因并发策略被跳过。"""

    trigger_name: str


@dataclass(frozen=True)
class TriggerCompleted:
    """触发器整链执行完毕。"""

    trigger_name: str
    elapsed: float


@dataclass(frozen=True)
class TriggerAborted:
    """触发器因条件未通过而中止。"""

    trigger_name: str
    condition_name: str


@dataclass(frozen=True)
class TriggerError:
    """触发器执行中出现未捕获异常。"""

    trigger_name: str
    error: Exception


@dataclass(frozen=True)
class ConditionChecked:
    """单条条件表达式已求值。"""

    trigger_name: str
    condition_name: str
    passed: bool


@dataclass(frozen=True)
class ActionStarted:
    """触发器内某个动作开始。"""

    trigger_name: str
    action_name: str
    params: dict | None = None


@dataclass(frozen=True)
class ActionCompleted:
    """触发器内某个动作完成。"""

    trigger_name: str
    action_name: str
    elapsed: float
    params: dict | None = None


@dataclass(frozen=True)
class ActionError:
    """触发器内某个动作失败。"""

    trigger_name: str
    action_name: str
    error: Exception


@dataclass(frozen=True)
class LoadError:
    """加载阶段失败。"""

    section: str
    instance: str
    phase: LoadPhase
    code: LoadErrorCode
    error: Exception


@dataclass(frozen=True)
class ObserverAfter:
    """observer 在方法调用完成后发出（after 阶段）。"""

    obs: ObserverContext


ListenerEvent = (
    Loaded
    | Started
    | Stopped
    | EventFired
    | TriggerStarted
    | TriggerSkipped
    | TriggerCompleted
    | TriggerAborted
    | TriggerError
    | ConditionChecked
    | ActionStarted
    | ActionCompleted
    | ActionError
    | LoadError
    | ObserverAfter
)
