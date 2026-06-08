from __future__ import annotations

import json
from typing import Any


class SourceNotImplementedError(NotImplementedError):
    """来源尚未实现对应能力。"""


class TikHubApiError(RuntimeError):
    """TikHub API 调用失败。"""

    def __init__(
        self,
        message: str,
        *,
        method: str | None = None,
        path: str | None = None,
        params: dict[str, Any] | None = None,
        http_status: int | None = None,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.path = path
        self.params = params
        self.http_status = http_status
        self.body = body

    def detail_lines(self) -> list[str]:
        """拼出含接口与响应 JSON 的多行说明。"""
        lines = [str(self)]
        if self.method and self.path:
            lines.append(f"接口: {self.method} {self.path}")
        elif self.path:
            lines.append(f"接口: {self.path}")
        if self.params is not None:
            lines.append(f"参数: {json.dumps(self.params, ensure_ascii=False)}")
        if self.http_status is not None:
            lines.append(f"HTTP 状态: {self.http_status}")
        if self.body is not None:
            lines.append("响应 JSON:")
            lines.append(json.dumps(self.body, ensure_ascii=False, indent=2))
        return lines


def format_platform_fetch_error(platform: str, exc: BaseException) -> str:
    """把单平台拉取异常格式化为可打印的多行文本。"""
    if isinstance(exc, TikHubApiError):
        return "\n".join([f"[{platform}]", *exc.detail_lines()])
    return f"[{platform}] {exc}"
