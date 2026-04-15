from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ObserverPhase = Literal["before", "after", "error"]
ObserverKind = Literal["instance", "class", "static"]


@dataclass(slots=True)
class ObserverContext:
    call_id: str
    instance: Any | None
    owner: Any | None
    cls: type
    cls_name: str
    method_name: str
    qualname: str
    method_kind: ObserverKind
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    result: Any = None
    error: BaseException | None = None
    phase: ObserverPhase = "after"
    is_async: bool = False
    started_at: float = 0.0
    ended_at: float = 0.0
    elapsed: float = 0.0