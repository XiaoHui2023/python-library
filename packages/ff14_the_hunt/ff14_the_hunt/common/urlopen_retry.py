from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from random import uniform

_RETRYABLE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})
_DEFAULT_MAX_ATTEMPTS = 4
_DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
_DEFAULT_MAX_BACKOFF_SECONDS = 8.0
_DEFAULT_MAX_RETRY_AFTER_SECONDS = 300.0
_DEFAULT_JITTER_RATIO = 0.15


def retry_after_seconds_from_headers(headers: object) -> float | None:
    if headers is None or not hasattr(headers, "get"):
        return None
    raw = headers.get("Retry-After")  # type: ignore[attr-defined]
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        seconds = retry_at.timestamp() - time.time()
    return max(0.0, seconds)


def is_retryable_urlopen_error(exc: BaseException) -> bool:
    """判断 ``urlopen`` 相关异常是否宜短暂等待后重试。"""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _RETRYABLE_HTTP_CODES
    if isinstance(exc, TimeoutError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, TimeoutError):
            return True
        if isinstance(reason, (ssl.SSLError, ConnectionResetError, OSError)):
            return True
        return True
    if isinstance(exc, (ssl.SSLError, ConnectionResetError, OSError)):
        return True
    return False


def urlopen_read(
    request: urllib.request.Request,
    *,
    timeout: float,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    initial_backoff_seconds: float = _DEFAULT_INITIAL_BACKOFF_SECONDS,
    max_backoff_seconds: float = _DEFAULT_MAX_BACKOFF_SECONDS,
    max_retry_after_seconds: float = _DEFAULT_MAX_RETRY_AFTER_SECONDS,
    jitter_ratio: float = _DEFAULT_JITTER_RATIO,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """``urlopen`` 读响应体；瞬时网络或 TLS 失败时指数退避重试。

    Args:
        request: 待发送请求。
        timeout: 单次 ``urlopen`` 超时秒数。
        max_attempts: 最多尝试次数（含首次）。
        initial_backoff_seconds: 首次重试前等待秒数。
        max_backoff_seconds: 退避等待上限秒数。

    Returns:
        响应体原始字节。

    Raises:
        urllib.error.HTTPError: 不可重试的 HTTP 状态，或重试耗尽后的 HTTP 错误。
        urllib.error.URLError: 重试耗尽后的网络或 TLS 错误。
        TimeoutError: 重试耗尽后的超时。
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if max_retry_after_seconds < 0:
        raise ValueError("max_retry_after_seconds must be >= 0")
    if jitter_ratio < 0:
        raise ValueError("jitter_ratio must be >= 0")

    last_exc: BaseException | None = None
    backoff = initial_backoff_seconds
    for attempt in range(max_attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except BaseException as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts or not is_retryable_urlopen_error(exc):
                raise
            wait_seconds = min(backoff, max_backoff_seconds)
            if isinstance(exc, urllib.error.HTTPError):
                retry_after = retry_after_seconds_from_headers(exc.headers)
                if retry_after is not None:
                    wait_seconds = min(retry_after, max_retry_after_seconds)
            if jitter_ratio > 0 and wait_seconds > 0:
                wait_seconds *= uniform(1.0 - jitter_ratio, 1.0 + jitter_ratio)
            sleep(wait_seconds)
            backoff = min(backoff * 2.0, max_backoff_seconds)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("urlopen_read ended without response or error")
