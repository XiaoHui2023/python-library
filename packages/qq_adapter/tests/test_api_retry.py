import asyncio
import unittest
from unittest.mock import patch

from qq_adapter.bot import QQBot


class _Response:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self._text = text

    async def text(self) -> str:
        return self._text


class _RequestContext:
    def __init__(self, response: _Response) -> None:
        self._response = response

    async def __aenter__(self) -> _Response:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _Session:
    closed = False

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def request(self, *args, **kwargs) -> _RequestContext:
        del args, kwargs
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _RequestContext(outcome)


class ApiRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_retries_and_returns_json(self) -> None:
        bot = QQBot("app", "secret", "bot")
        session = _Session([asyncio.TimeoutError(), _Response(200, '{"ok": true}')])
        bot._session = session  # type: ignore[assignment]

        with patch("qq_adapter.bot.API_RETRY_DELAYS", (0, 0)):
            result = await bot._request_json("POST", "https://example.test/api")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(session.calls, 2)

    async def test_retryable_status_retries_and_returns_json(self) -> None:
        bot = QQBot("app", "secret", "bot")
        session = _Session([_Response(503, "busy"), _Response(200, '{"ok": true}')])
        bot._session = session  # type: ignore[assignment]

        with patch("qq_adapter.bot.API_RETRY_DELAYS", (0, 0)):
            result = await bot._request_json("GET", "https://example.test/api")

        self.assertEqual(result, {"ok": True})
        self.assertEqual(session.calls, 2)

    async def test_client_error_status_does_not_retry(self) -> None:
        bot = QQBot("app", "secret", "bot")
        session = _Session([_Response(400, "bad request")])
        bot._session = session  # type: ignore[assignment]

        with self.assertRaisesRegex(RuntimeError, "400 bad request"):
            await bot._request_json("POST", "https://example.test/api")

        self.assertEqual(session.calls, 1)


if __name__ == "__main__":
    unittest.main()
