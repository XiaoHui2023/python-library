from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .base import BaseListener


class ConsoleListener(BaseListener):
    """使用 Rich 的默认控制台输出，便于阅读。"""

    def __init__(self) -> None:
        self._con = Console(stderr=True, highlight=False)

    def on_loaded(self, context) -> None:
        self._con.print(
            Panel.fit(
                "📦 [bold cyan]配置已加载[/] · 实体/事件/触发器已就绪",
                border_style="dim cyan",
            )
        )

    def on_started(self) -> None:
        self._con.print("🚀 [bold green]自动化已启动[/]")

    def on_stopped(self) -> None:
        self._con.print("🛑 [dim]自动化已停止[/]")

    def on_event_fired(self, event_name: str, data: dict[str, Any]) -> None:
        self._con.print(Text.assemble("⚡ ", (event_name, "bold cyan")))

    def on_trigger_started(self, trigger_name: str) -> None:
        self._con.print(
            Panel(
                f"▶️ [yellow]{trigger_name}[/] 开始执行",
                border_style="yellow",
                padding=(0, 1),
            )
        )

    def on_trigger_skipped(self, trigger_name: str) -> None:
        self._con.print(f"⏭️  [dim]{trigger_name}[/] 跳过（并发占用中）")

    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None:
        t = f" ({elapsed:.2f}s)" if elapsed >= 0.005 else ""
        self._con.print(f"✅ [green]{trigger_name}[/] 完成{t}")

    def on_trigger_aborted(self, trigger_name: str, condition_name: str) -> None:
        self._con.print(
            f"🧱 [yellow]{trigger_name}[/] 中止 · 条件 [magenta]{condition_name}[/]"
        )

    def on_trigger_error(self, trigger_name: str, error: Exception) -> None:
        self._con.print(f"💥 [red]{trigger_name}[/] 错误: {error!s}")

    def on_condition_checked(
        self, trigger_name: str, condition_name: str, passed: bool
    ) -> None:
        icon = "✔️" if passed else "✖️"
        style = "green" if passed else "red"
        self._con.print(
            f"  {icon} [{style}]{condition_name}[/] [dim]· {trigger_name}[/]"
        )

    def on_action_started(
        self, trigger_name: str, action_name: str, params: dict | None
    ) -> None:
        self._con.print(f"  🔹 [blue]{action_name}[/] [dim]← {trigger_name}[/]")

    def on_action_completed(
        self,
        trigger_name: str,
        action_name: str,
        elapsed: float,
        params: dict | None,
    ) -> None:
        t = f" ({elapsed:.2f}s)" if elapsed >= 0.005 else ""
        self._con.print(f"  ✔️ [green]{action_name}[/] 完成{t}")

    def on_action_error(
        self, trigger_name: str, action_name: str, error: Exception
    ) -> None:
        self._con.print(
            f"  ❌ [red]{action_name}[/] 失败 [dim]← {trigger_name}[/]: {error!s}"
        )

    def on_load_error(self, section, instance, phase, code, error):
        self._con.print(
            f"🚫 [red]{section}.{instance}[/] [{phase}/{code}]: {error!s}"
        )

    def on_observer_after(self, obs) -> None:
        if obs.instance is None:
            return
        name = getattr(obs.instance, "instance_name", "?")
        self._con.print(
            f"👁️ [dim]{name}[/].[cyan]{obs.method_name}[/] [dim]({obs.elapsed*1000:.1f}ms)[/]"
        )
