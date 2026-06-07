from __future__ import annotations

import json

from ai_agent import AgentListener, RunOutputPacket
from ai_agent.context import RunContext, RunStatus, ToolInvocation

from examples._support.print_timing import ExamplePrintTiming


def create_print_listener(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timing: ExamplePrintTiming | None = None,
) -> tuple[AgentListener, ExamplePrintTiming]:
    """
    示例用终端 listener：打印思考/回答流、工具调用与终稿。

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
    stream_section: str | None = None

    def _ts() -> str:
        return clock.tag()

    def _println(text: str = "") -> None:
        if text:
            print(f"{_ts()} {text}")
        else:
            print()

    def _section(title: str) -> None:
        _println(f"--- {title} ---")

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

    def on_run_start(run: RunContext) -> None:
        nonlocal thinking_open, output_open
        _close_stream_section()
        thinking_open = False
        output_open = False
        _println()
        _section("运行 · 上下文")
        _print_user_messages(run)

    def on_thinking_delta(delta: str, run: RunContext) -> None:
        del run
        _open_stream("运行 · 思考")
        print(delta, end="", flush=True)

    def on_output_delta(delta: str, run: RunContext) -> None:
        del run
        _open_stream("运行 · 回答")
        print(delta, end="", flush=True)

    def on_tool_start(invocation: ToolInvocation, run: RunContext) -> None:
        del run
        _close_stream_section()
        _println()
        _section(f"运行 · 工具: {invocation.tool_name}")
        _println(f"args: {json.dumps(invocation.arguments, ensure_ascii=False)}")

    def on_tool_end(invocation: ToolInvocation, run: RunContext) -> None:
        del run
        label = "ok" if invocation.ok else "fail"
        _println(f"{label}: {invocation.answer}")

    def on_run_end(run: RunContext) -> None:
        _close_stream_section()
        _println()
        _section("运行 · 结束")
        _println(f"status: {run.status.value}")
        if run.output:
            preview = run.output.strip()
            if len(preview) > 200:
                preview = preview[:200] + "…"
            _println(f"output: {preview}")
        elif run.status != RunStatus.COMPLETED:
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
        on_run_start=on_run_start,
        on_thinking_delta=on_thinking_delta,
        on_output_delta=on_output_delta,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_run_end=on_run_end,
        on_app_run_end=on_app_run_end,
    )
    return listener, clock
