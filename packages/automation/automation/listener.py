from __future__ import annotations

import sys


class AutomationListener:
    """自动化生命周期监听器 — 子类覆写感兴趣的方法"""

    def on_start(self) -> None: pass
    def on_stop(self) -> None: pass
    def on_event_fired(self, event_name: str) -> None: pass
    def on_trigger_started(self, trigger_name: str) -> None: pass
    def on_trigger_skipped(self, trigger_name: str) -> None: pass
    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None: pass
    def on_trigger_aborted(self, trigger_name: str, condition_name: str) -> None: pass
    def on_trigger_error(self, trigger_name: str, error: Exception) -> None: pass
    def on_condition_checked(self, trigger_name: str, condition_name: str, passed: bool) -> None: pass
    def on_action_started(self, trigger_name: str, action_name: str) -> None: pass
    def on_action_completed(self, trigger_name: str, action_name: str, elapsed: float) -> None: pass
    def on_action_error(self, trigger_name: str, action_name: str, error: Exception) -> None: pass


class _Ansi:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    CYAN   = "\033[36m"


class ConsoleRenderer(AutomationListener):
    """默认彩色控制台渲染器"""

    def _write(self, msg: str) -> None:
        sys.stderr.write(msg + "\n")
        sys.stderr.flush()

    def on_start(self) -> None:
        self._write(f"{_Ansi.DIM}── Assistant started ──{_Ansi.RESET}")

    def on_stop(self) -> None:
        self._write(f"{_Ansi.DIM}── Assistant stopped ──{_Ansi.RESET}")

    def on_event_fired(self, event_name: str) -> None:
        self._write(f"{_Ansi.CYAN}{_Ansi.BOLD}⚡ {event_name}{_Ansi.RESET}")

    def on_trigger_started(self, trigger_name: str) -> None:
        self._write(f"{_Ansi.YELLOW}┌ {trigger_name}{_Ansi.RESET}")

    def on_trigger_skipped(self, trigger_name: str) -> None:
        self._write(f"{_Ansi.DIM}⏭ {trigger_name} (busy){_Ansi.RESET}")

    def on_trigger_completed(self, trigger_name: str, elapsed: float) -> None:
        self._write(
            f"{_Ansi.YELLOW}└ {trigger_name}{_Ansi.RESET}"
            f" {_Ansi.DIM}({elapsed:.2f}s){_Ansi.RESET}"
        )

    def on_trigger_aborted(self, trigger_name: str, condition_name: str) -> None:
        self._write(
            f"{_Ansi.YELLOW}└ {trigger_name}{_Ansi.RESET}"
            f" {_Ansi.DIM}aborted by {condition_name}{_Ansi.RESET}"
        )

    def on_trigger_error(self, trigger_name: str, error: Exception) -> None:
        self._write(
            f"{_Ansi.YELLOW}└ {trigger_name}{_Ansi.RESET}"
            f" {_Ansi.RED}error{_Ansi.RESET}"
        )

    def on_condition_checked(
        self, trigger_name: str, condition_name: str, passed: bool
    ) -> None:
        if passed:
            self._write(f"{_Ansi.GREEN}│ ✓ {condition_name}{_Ansi.RESET}")
        else:
            self._write(f"{_Ansi.RED}│ ✗ {condition_name}{_Ansi.RESET}")

    def on_action_started(self, trigger_name: str, action_name: str) -> None:
        self._write(f"│ ▶ {action_name}")

    def on_action_completed(
        self, trigger_name: str, action_name: str, elapsed: float
    ) -> None:
        self._write(
            f"{_Ansi.GREEN}│ ✓ {action_name}{_Ansi.RESET}"
            f" {_Ansi.DIM}({elapsed:.2f}s){_Ansi.RESET}"
        )

    def on_action_error(
        self, trigger_name: str, action_name: str, error: Exception
    ) -> None:
        self._write(f"{_Ansi.RED}│ ✗ {action_name}: {error}{_Ansi.RESET}")