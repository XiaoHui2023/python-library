from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, PrivateAttr

from automation.listener.events import ActionCompleted, ActionError, ActionStarted

from .base import BaseAutomation

if TYPE_CHECKING:
    from automation.core.renderer import Renderer
    from automation.runtime.context import Context


class Action(BaseAutomation):
    """自动化动作基类：子类实现 execute；组合由触发器上的动作列表或用户派生类承担。"""

    _runtime_renderer: Renderer | None = PrivateAttr(default=None)

    @property
    def display_label(self) -> str:
        """监听事件展示用的一步标识。"""

        return type(self).__name__

    @property
    def log_params(self) -> dict[str, Any]:
        """监听事件中附带展示的参数字典。"""

        return {}

    def _bind_runtime_renderer(self, renderer: Renderer | None) -> None:
        self._runtime_renderer = renderer

    def _require_renderer(self) -> Renderer:
        renderer = self._runtime_renderer
        if renderer is None:
            raise RuntimeError("动作运行前未绑定渲染器")
        return renderer

    async def execute(self, renderer: Renderer) -> None:
        """在已绑定渲染器下执行本步语义；子类必须实现。"""

        raise NotImplementedError(
            f"{type(self).__name__} must implement execute()"
        )

    async def run_phased_execute(self, renderer: Renderer) -> None:
        """构建 → 校验 → 激活 → 运行 → 反激活（触发器内联一步常用）。"""

        self._bind_runtime_renderer(renderer)
        try:
            await self.build_phase()
            await self.validate_phase()
            await self.activate_phase()
            try:
                await self.run_phase()
            finally:
                await self.inactive_phase()
        finally:
            self._bind_runtime_renderer(None)

    async def on_run(self, *, closing: bool = False) -> None:
        if closing:
            return
        await self.execute(self._require_renderer())


class InstrumentedActionRun(Action):
    """触发器内联一步：包装内层动作并发出监听与计时事件。"""

    emit_trigger_name: str = Field(exclude=True, repr=False)
    emit_label: str = Field(exclude=True, repr=False)
    emit_params: dict[str, Any] = Field(exclude=True, repr=False, default_factory=dict)

    _inner: Action = PrivateAttr()

    @classmethod
    def wrap(
        cls,
        *,
        instance_name: str,
        context: Context,
        inner: Action,
        trigger_name: str,
    ) -> InstrumentedActionRun:
        return cls(
            instance_name=instance_name,
            _ctx=context,
            emit_trigger_name=trigger_name,
            emit_label=inner.display_label,
            emit_params=inner.log_params,
            _inner=inner,
        )

    async def on_build(self) -> None:
        await self._inner.build_phase()

    async def validate_phase(self) -> None:
        await self._inner.validate_phase()

    async def run_phased_execute(self, renderer: Renderer) -> None:
        self._bind_runtime_renderer(renderer)
        self._inner._bind_runtime_renderer(renderer)
        inner_ok = False
        try:
            await self.before_run()
            try:
                await self._inner.run_phased_execute(renderer)
                inner_ok = True
            except Exception as e:
                self._ctx.clear_action_step_timer()
                self._ctx.emit(
                    ActionError(self.emit_trigger_name, self.emit_label, e),
                )
                raise
            finally:
                if inner_ok:
                    elapsed = self._ctx.consume_action_step_elapsed()
                    self._ctx.emit(
                        ActionCompleted(
                            self.emit_trigger_name,
                            self.emit_label,
                            elapsed,
                            params=self.emit_params,
                        )
                    )
        finally:
            self._inner._bind_runtime_renderer(None)
            self._bind_runtime_renderer(None)

    async def before_run(self, *, closing: bool = False) -> None:
        if closing:
            return
        self._ctx.mark_action_step_start()
        self._ctx.emit(
            ActionStarted(
                self.emit_trigger_name,
                self.emit_label,
                params=self.emit_params,
            )
        )
