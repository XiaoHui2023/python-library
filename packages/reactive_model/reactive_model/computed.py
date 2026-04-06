from __future__ import annotations

from typing import Callable, TypeVar, cast

from .reactive import ReactiveModel
from .track import Collector, Trackable, compute_context, track

T = TypeVar("T")
_MISSING = object()


class ComputedModel(ReactiveModel[T]):
    def __init__(self, expr: Callable[[], T]) -> None:
        super().__init__()
        self._expr = expr
        self._cache: T | object = _MISSING
        self._deps: dict[int, tuple[Trackable, int]] = {}

    @property
    def value(self) -> T:
        if self._needs_recompute():
            self._recompute()
        track(self)
        return cast(T, self._cache)

    @property
    def version(self) -> int:
        if self._needs_recompute():
            self._recompute()
        return super().version

    def _needs_recompute(self) -> bool:
        if self._cache is _MISSING:
            return True

        for dep, captured_version in self._deps.values():
            if dep.version != captured_version:
                return True

        return False

    def _recompute(self) -> None:
        collector = Collector()

        with compute_context(self, collector):
            new_value = self._expr()

        new_deps: dict[int, tuple[Trackable, int]] = {}
        for dep_id, dep in collector.deps.items():
            new_deps[dep_id] = (dep, dep.version)

        self._deps = new_deps
        self._cache = new_value

        self.touch()