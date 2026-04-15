from __future__ import annotations

import functools
import inspect
import time
import uuid
from collections.abc import Callable
from typing import Any

from .bus import ObserverBus
from .context import ObserverContext, ObserverKind, ObserverPhase


_WRAPPED_FLAG = "__observer_bus_wrapped__"
_SUBCLASS_HOOK_FLAG = "__observer_bus_subclass_hook_installed__"


def observe_methods(
    bus: ObserverBus,
    *,
    include_private: bool = False,
    emit_before: bool = True,
):
    def decorator(cls: type) -> type:
        _observe_class(
            cls,
            bus=bus,
            include_private=include_private,
            emit_before=emit_before,
        )
        _install_subclass_hook(
            cls,
            bus=bus,
            include_private=include_private,
            emit_before=emit_before,
        )
        return cls

    return decorator


def _install_subclass_hook(
    cls: type,
    *,
    bus: ObserverBus,
    include_private: bool,
    emit_before: bool,
) -> None:
    if cls.__dict__.get(_SUBCLASS_HOOK_FLAG, False):
        return

    original_init_subclass = cls.__dict__.get("__init_subclass__")

    @classmethod
    def __init_subclass__(subcls, **kwargs):
        if original_init_subclass is not None:
            original_init_subclass.__get__(subcls, subcls)(**kwargs)
        else:
            super(cls, subcls).__init_subclass__(**kwargs)

        _observe_class(
            subcls,
            bus=bus,
            include_private=include_private,
            emit_before=emit_before,
        )
        _install_subclass_hook(
            subcls,
            bus=bus,
            include_private=include_private,
            emit_before=emit_before,
        )

    setattr(cls, "__init_subclass__", __init_subclass__)
    setattr(cls, _SUBCLASS_HOOK_FLAG, True)


def _observe_class(
    cls: type,
    *,
    bus: ObserverBus,
    include_private: bool,
    emit_before: bool,
) -> None:
    for name, obj in list(cls.__dict__.items()):
        if not include_private and name.startswith("_"):
            continue

        if isinstance(obj, property):
            continue

        if isinstance(obj, staticmethod):
            func = obj.__func__
            if getattr(func, _WRAPPED_FLAG, False):
                continue
            wrapped_func = _wrap_function(
                owner_cls=cls,
                method_name=name,
                func=func,
                bus=bus,
                method_kind="static",
                emit_before=emit_before,
            )
            setattr(cls, name, staticmethod(wrapped_func))
            continue

        if isinstance(obj, classmethod):
            func = obj.__func__
            if getattr(func, _WRAPPED_FLAG, False):
                continue
            wrapped_func = _wrap_function(
                owner_cls=cls,
                method_name=name,
                func=func,
                bus=bus,
                method_kind="class",
                emit_before=emit_before,
            )
            setattr(cls, name, classmethod(wrapped_func))
            continue

        if callable(obj):
            if getattr(obj, _WRAPPED_FLAG, False):
                continue
            wrapped = _wrap_function(
                owner_cls=cls,
                method_name=name,
                func=obj,
                bus=bus,
                method_kind="instance",
                emit_before=emit_before,
            )
            setattr(cls, name, wrapped)


def _wrap_function(
    owner_cls: type,
    method_name: str,
    func: Callable[..., Any],
    bus: ObserverBus,
    method_kind: ObserverKind,
    emit_before: bool,
):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            call_id = uuid.uuid4().hex
            started = time.perf_counter()

            if emit_before:
                bus.emit(
                    _build_context(
                        owner_cls=owner_cls,
                        method_name=method_name,
                        func=func,
                        method_kind=method_kind,
                        args=args,
                        kwargs=kwargs,
                        phase="before",
                        is_async=True,
                        started_at=started,
                        call_id=call_id,
                    )
                )

            try:
                result = await func(*args, **kwargs)
            except Exception as error:
                ended = time.perf_counter()
                bus.emit(
                    _build_context(
                        owner_cls=owner_cls,
                        method_name=method_name,
                        func=func,
                        method_kind=method_kind,
                        args=args,
                        kwargs=kwargs,
                        phase="error",
                        is_async=True,
                        started_at=started,
                        ended_at=ended,
                        error=error,
                        call_id=call_id,
                    )
                )
                raise

            ended = time.perf_counter()
            bus.emit(
                _build_context(
                    owner_cls=owner_cls,
                    method_name=method_name,
                    func=func,
                    method_kind=method_kind,
                    args=args,
                    kwargs=kwargs,
                    phase="after",
                    is_async=True,
                    started_at=started,
                    ended_at=ended,
                    result=result,
                    call_id=call_id,
                )
            )
            return result

        setattr(async_wrapper, _WRAPPED_FLAG, True)
        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        call_id = uuid.uuid4().hex
        started = time.perf_counter()

        if emit_before:
            bus.emit(
                _build_context(
                    owner_cls=owner_cls,
                    method_name=method_name,
                    func=func,
                    method_kind=method_kind,
                    args=args,
                    kwargs=kwargs,
                    phase="before",
                    is_async=False,
                    started_at=started,
                    call_id=call_id,
                )
            )

        try:
            result = func(*args, **kwargs)
        except Exception as error:
            ended = time.perf_counter()
            bus.emit(
                _build_context(
                    owner_cls=owner_cls,
                    method_name=method_name,
                    func=func,
                    method_kind=method_kind,
                    args=args,
                    kwargs=kwargs,
                    phase="error",
                    is_async=False,
                    started_at=started,
                    ended_at=ended,
                    error=error,
                    call_id=call_id,
                )
            )
            raise

        ended = time.perf_counter()
        bus.emit(
            _build_context(
                owner_cls=owner_cls,
                method_name=method_name,
                func=func,
                method_kind=method_kind,
                args=args,
                kwargs=kwargs,
                phase="after",
                is_async=False,
                started_at=started,
                ended_at=ended,
                result=result,
                call_id=call_id,
            )
        )
        return result

    setattr(sync_wrapper, _WRAPPED_FLAG, True)
    return sync_wrapper


def _build_context(
    *,
    owner_cls: type,
    method_name: str,
    func: Callable[..., Any],
    method_kind: ObserverKind,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    phase: ObserverPhase,
    is_async: bool,
    started_at: float,
    call_id: str,
    ended_at: float | None = None,
    result: Any = None,
    error: BaseException | None = None,
) -> ObserverContext:
    instance, owner, pure_args = _split_receiver(method_kind, args)
    actual_cls = _resolve_context_class(
        owner_cls=owner_cls,
        method_kind=method_kind,
        instance=instance,
        owner=owner,
    )
    final_ended_at = ended_at if ended_at is not None else 0.0
    elapsed = final_ended_at - started_at if ended_at is not None else 0.0

    return ObserverContext(
        call_id=call_id,
        instance=instance,
        owner=owner,
        cls=actual_cls,
        cls_name=actual_cls.__name__,
        method_name=method_name,
        qualname=func.__qualname__,
        method_kind=method_kind,
        args=pure_args,
        kwargs=dict(kwargs),
        result=result,
        error=error,
        phase=phase,
        is_async=is_async,
        started_at=started_at,
        ended_at=final_ended_at,
        elapsed=elapsed,
    )


def _split_receiver(
    method_kind: ObserverKind,
    args: tuple[Any, ...],
) -> tuple[Any | None, Any | None, tuple[Any, ...]]:
    if method_kind == "instance":
        instance = args[0] if args else None
        pure_args = args[1:] if args else ()
        return instance, instance, pure_args

    if method_kind == "class":
        owner = args[0] if args else None
        pure_args = args[1:] if args else ()
        return None, owner, pure_args

    return None, None, args


def _resolve_context_class(
    *,
    owner_cls: type,
    method_kind: ObserverKind,
    instance: Any | None,
    owner: Any | None,
) -> type:
    if method_kind == "instance" and instance is not None:
        return type(instance)

    if method_kind == "class" and isinstance(owner, type):
        return owner

    return owner_cls