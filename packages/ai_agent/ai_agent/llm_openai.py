from __future__ import annotations

import json
from typing import Any, AsyncIterator

from ai_agent.context import RunContext
from ai_agent.llm import StreamChunk, StreamKind


def _merge_extra_body(kwargs: dict[str, Any], patch: dict[str, Any]) -> None:
    extra = dict(kwargs.get("extra_body") or {})
    extra.update(patch)
    kwargs["extra_body"] = extra


def _apply_thinking_kwargs(kwargs: dict[str, Any], *, base_url: str) -> None:
    """按网关形态写入思考模式参数（DeepSeek 用 extra_body，其余兼容端用 enable_thinking）。"""
    if "deepseek" in base_url.lower():
        _merge_extra_body(kwargs, {"thinking": {"type": "enabled"}})
        return
    kwargs["enable_thinking"] = True


class OpenAILLM:
    """库内：包装 ``AsyncOpenAI``，将官方流式事件映射为 ``StreamChunk``。"""

    def __init__(
        self,
        client: Any,
        *,
        model: str,
        base_url: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        thinking_enabled: bool = False,
    ) -> None:
        self._client = client
        self.model = model
        self._base_url = base_url.strip()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.thinking_enabled = thinking_enabled

    async def stream(
        self,
        context: RunContext,
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": context.api_messages(),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.thinking_enabled:
            _apply_thinking_kwargs(kwargs, base_url=self._base_url)

        stream = await self._client.chat.completions.create(**kwargs)
        tool_bufs: dict[int, dict[str, Any]] = {}

        async for event in stream:
            if not event.choices:
                continue
            choice = event.choices[0]
            delta = choice.delta

            if delta.content:
                yield StreamChunk(kind=StreamKind.TEXT, delta=delta.content)

            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield StreamChunk(kind=StreamKind.REASONING, delta=reasoning)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = int(tc.index or 0)
                    buf = tool_bufs.setdefault(
                        idx,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if tc.id:
                        buf["id"] = tc.id
                    if tc.function and tc.function.name:
                        buf["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        buf["arguments"] += tc.function.arguments

            if choice.finish_reason == "tool_calls":
                async for chunk in _flush_tool_bufs(tool_bufs):
                    yield chunk
                tool_bufs.clear()

        async for chunk in _flush_tool_bufs(tool_bufs):
            yield chunk
        yield StreamChunk(kind=StreamKind.DONE)


async def _flush_tool_bufs(tool_bufs: dict[int, dict[str, Any]]) -> AsyncIterator[StreamChunk]:
    for buf in tool_bufs.values():
        args_raw = buf.get("arguments") or "{}"
        try:
            args = json.loads(args_raw)
        except json.JSONDecodeError:
            args = {}
        if buf.get("id") and buf.get("name"):
            yield StreamChunk(
                kind=StreamKind.TOOL_CALL,
                tool_call_id=buf["id"],
                tool_name=buf["name"],
                tool_arguments=args if isinstance(args, dict) else {},
            )
