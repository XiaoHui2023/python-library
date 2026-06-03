from __future__ import annotations

import json
from typing import Literal

from ai_agent import AgentListener, RunOutputPacket
from ai_agent.context import RunContext, RunPhaseKind, RunStatus, ToolInvocation
from ai_agent.plan.display import format_plan_for_terminal
from ai_agent.plan.models import Plan, PlanStep

from examples._support.print_timing import ExamplePrintTiming

_StepStatus = Literal["pending", "running", "done", "skipped"]


def create_print_listener(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timing: ExamplePrintTiming | None = None,
) -> tuple[AgentListener, ExamplePrintTiming]:
    """
    示例用终端 listener：按前端可对接的事件顺序打印规划与步骤的思考/回答流、
    步骤进度、工具与交付物。

    Args:
        model: 可选，运行开始时打印的模型名
        base_url: 可选，运行开始时打印的 API 地址
        timing: 可选，与入口共用的轮次计时；未传则新建

    Returns:
        listener 与同一 ``ExamplePrintTiming`` 实例（入口在 ``app.run`` 前须 ``reset()``）
    """
    clock = timing if timing is not None else ExamplePrintTiming()
    thinking_open = False
    output_open = False
    current_plan: Plan | None = None
    step_statuses: list[_StepStatus] = []
    active_step_index: int | None = None
    stream_section: str | None = None

    def _ts() -> str:
        return clock.tag()

    def _println(text: str = "") -> None:
        if text:
            print(f"{_ts()} {text}")
        else:
            print()

    def _print_block(text: str) -> None:
        lines = text.splitlines() or [""]
        _println(lines[0])
        for line in lines[1:]:
            print(line)

    def _section(title: str) -> None:
        _println(f"--- {title} ---")

    def _phase_label(run: RunContext) -> str:
        phase = run.phase
        if phase is None:
            return "运行"
        if phase.kind == RunPhaseKind.PLANNING:
            return "规划"
        if phase.kind == RunPhaseKind.STEP and phase.step_index is not None:
            total = len(current_plan.steps) if current_plan else "?"
            return f"步骤 {phase.step_index + 1}/{total}"
        return "运行"

    def _close_stream_section() -> None:
        nonlocal thinking_open, output_open, stream_section
        if thinking_open or output_open:
            print()
        thinking_open = False
        output_open = False
        stream_section = None

    def _open_stream(section: str) -> None:
        nonlocal thinking_open, output_open, stream_section
        if stream_section != section:
            _close_stream_section()
            _println()
            _section(section)
            stream_section = section
            thinking_open = section.endswith("思考")
            output_open = section.endswith("回答")

    def _print_role_message(role: str, content: str) -> None:
        lines = content.splitlines() or [""]
        _println(f"{role}: {lines[0]}")
        indent = " " * (len(role) + 2)
        for line in lines[1:]:
            print(f"{indent}{line}")

    def _print_user_messages(run: RunContext) -> None:
        if model and base_url:
            _println(f"model: {model} @ {base_url}")
        elif model:
            _println(f"model: {model}")
        for message in run.messages:
            _print_role_message(message.role, message.content)

    def _format_progress_line(index: int, step: PlanStep, status: _StepStatus) -> str:
        markers = {
            "pending": "[ ]",
            "running": "[>]",
            "done": "[✓]",
            "skipped": "[−]",
        }
        optional_tag = "（可选）" if step.optional else ""
        return (
            f"  {markers[status]} {index + 1}. {step.id} · {step.title}{optional_tag}"
        )

    def _print_plan_progress(highlight: int | None = None) -> None:
        if current_plan is None:
            return
        _println()
        _section("计划进度")
        for index, step in enumerate(current_plan.steps):
            status = step_statuses[index] if index < len(step_statuses) else "pending"
            if highlight is not None and index == highlight:
                status = "running"
            _println(_format_progress_line(index, step, status))

    def on_plan_start() -> None:
        nonlocal current_plan, step_statuses, active_step_index
        _close_stream_section()
        current_plan = None
        step_statuses = []
        active_step_index = None
        _println()
        _section("规划")
        _println("正在分析任务并生成步骤…")

    def on_plan_ready(plan: Plan) -> None:
        nonlocal current_plan, step_statuses
        _close_stream_section()
        current_plan = plan
        step_statuses = ["pending"] * len(plan.steps)
        _print_block(format_plan_for_terminal(plan))
        _print_plan_progress()

    def on_plan_step_start(step_index: int, step: PlanStep, plan: Plan) -> None:
        nonlocal active_step_index
        del step, plan
        _close_stream_section()
        active_step_index = step_index
        if step_index < len(step_statuses):
            step_statuses[step_index] = "running"
        _print_plan_progress(highlight=step_index)

    def on_plan_step_end(
        step_index: int,
        step: PlanStep,
        plan: Plan,
        output: str,
        skipped: bool,
    ) -> None:
        del step, plan, output
        _close_stream_section()
        if step_index < len(step_statuses):
            step_statuses[step_index] = "skipped" if skipped else "done"
        tag = "已跳过" if skipped else "已完成"
        _println()
        _section(f"步骤 {step_index + 1} {tag}")
        _print_plan_progress()

    def on_run_start(run: RunContext) -> None:
        nonlocal thinking_open, output_open
        _close_stream_section()
        thinking_open = False
        output_open = False
        label = _phase_label(run)
        _println()
        _section(f"{label} · 上下文")
        _print_user_messages(run)

    def on_thinking_delta(delta: str, run: RunContext) -> None:
        label = _phase_label(run)
        _open_stream(f"{label} · 思考")
        print(delta, end="", flush=True)

    def on_output_delta(delta: str, run: RunContext) -> None:
        label = _phase_label(run)
        _open_stream(f"{label} · 回答")
        print(delta, end="", flush=True)

    def on_tool_start(invocation: ToolInvocation, run: RunContext) -> None:
        _close_stream_section()
        label = _phase_label(run)
        _println()
        _section(f"{label} · 工具: {invocation.tool_name}")
        _println(f"args: {json.dumps(invocation.arguments, ensure_ascii=False)}")

    def on_tool_end(invocation: ToolInvocation, run: RunContext) -> None:
        del run
        label = "ok" if invocation.ok else "fail"
        _println(f"{label}: {invocation.answer}")

    def on_run_end(run: RunContext) -> None:
        _close_stream_section()
        label = _phase_label(run)
        _println()
        _section(f"{label} · 结束")
        _println(f"status: {run.status.value}")
        if run.output and run.phase and run.phase.kind != RunPhaseKind.PLANNING:
            preview = run.output.strip()
            if len(preview) > 200:
                preview = preview[:200] + "…"
            _println(f"output: {preview}")
        elif run.status != RunStatus.COMPLETED and not run.output:
            _println("output: (empty)")

    def on_app_run_end(packet: RunOutputPacket) -> None:
        _close_stream_section()
        _println()
        _section("最终回答")
        _println(packet.answer.strip() or "(empty)")
        _println()
        _section("输出文件")
        if packet.output_files:
            for path in packet.output_files:
                _println(f"  {path}")
        else:
            _println("  (无)")
        _println(f"本轮总耗时: {clock.elapsed_s():.3f}s")

    listener = AgentListener(
        on_plan_start=on_plan_start,
        on_plan_ready=on_plan_ready,
        on_plan_step_start=on_plan_step_start,
        on_plan_step_end=on_plan_step_end,
        on_run_start=on_run_start,
        on_thinking_delta=on_thinking_delta,
        on_output_delta=on_output_delta,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_run_end=on_run_end,
        on_app_run_end=on_app_run_end,
    )
    return listener, clock
