from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ObserverPhase = Literal["before", "after", "error"]
ObserverKind = Literal["instance", "class", "static"]


@dataclass(slots=True)
class ObserverContext:
    """一次方法被观测时，某一时刻要交给监听者的信息包。"""

    # 标识与归属
    call_id: str
    """同一次调用共用的编号，before/after/error 对得上"""
    instance: Any | None
    """实例方法里的 self；不是实例方法则为空"""
    owner: Any | None
    """类方法里的类；其它情况多为空"""
    cls: type
    """当作哪个类来记；实例上一般是真实类型"""
    cls_name: str
    """类名，用来过滤、打印"""
    method_name: str
    """方法短名，用来过滤"""
    qualname: str
    """带类前缀的方法名"""
    method_kind: ObserverKind
    """实例 / 类方法 / 静态"""
    # 载荷
    args: tuple[Any, ...]
    """位置参数（已去掉 self/cls 这类接收者）"""
    kwargs: dict[str, Any]
    """关键字参数"""
    result: Any = None
    """正常返回时的结果；还没执行完可能没有"""
    error: BaseException | None = None
    """出错时的异常；没出错为空"""
    # 阶段与时间
    phase: ObserverPhase = "after"
    """before、after、error 三选一"""
    is_async: bool = False
    """是不是 async 方法"""
    started_at: float = 0.0
    """开始时刻（性能计数器）"""
    ended_at: float = 0.0
    """结束时刻；刚开始还没结束可能是 0"""
    elapsed: float = 0.0
    """这段调用花了多少秒"""
