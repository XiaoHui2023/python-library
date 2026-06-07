from __future__ import annotations

from ff14_the_hunt.models import (
    SpawnWindowPhase,
    TimerBarColor,
    TimerDisplay,
    TimerKind,
)

BEAR_TRACKER_BAR_HEX: dict[TimerBarColor, str] = {
    TimerBarColor.ERROR: "#e31a1a",
    TimerBarColor.SUCCESS: "#01b574",
    TimerBarColor.INFO: "#0075ff",
    TimerBarColor.WARNING: "#ffb547",
}


def bar_hex(color: TimerBarColor) -> str:
    return BEAR_TRACKER_BAR_HEX[color]


def build_timer_display(
    *,
    kind: TimerKind,
    phase: SpawnWindowPhase | None,
    bar_color: TimerBarColor,
    counts_up: bool,
    summary: str = "",
    elapsed_seconds: float | None = None,
    remaining_seconds: float | None = None,
    progress_percent: float | None = None,
) -> TimerDisplay:
    return TimerDisplay(
        kind=kind,
        label=kind.value,
        phase=phase,
        bar_color=bar_color,
        hex_color=bar_hex(bar_color),
        counts_up=counts_up,
        elapsed_seconds=elapsed_seconds,
        remaining_seconds=remaining_seconds,
        progress_percent=progress_percent,
        summary=summary,
    )
