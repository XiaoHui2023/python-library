import unittest
from unittest.mock import patch

from napcat_adapter.bot import Bot
from napcat_adapter.models import BotMessage, MessageType
from napcat_adapter.protocol_adapt import onebot_to_bot
from onebot_protocol import ImageMessageSegment, MessagePayload
from onebot_protocol.models import ImageSegmentData


class NapCatSendFailuresTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_raises_when_client_is_not_connected(self) -> None:
        bot = Bot(ws_url="ws://127.0.0.1:3001")
        message = BotMessage(
            message_id="m1",
            data_list=[{"type": "text", "data": {"text": "hello"}}],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with self.assertRaisesRegex(RuntimeError, "not connected"):
            await bot.send(message)

    async def test_group_send_retries_timeout_and_succeeds(self) -> None:
        bot = Bot(ws_url="ws://127.0.0.1:3001")
        client = _RetryingClient([TimeoutError(), TimeoutError(), {"message_id": 1}])
        bot._client = client  # type: ignore[assignment]
        message = BotMessage(
            message_id="m1",
            data_list=[{"type": "text", "data": {"text": "hello"}}],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with patch("napcat_adapter.bot.SEND_RETRY_DELAYS", (0, 0)):
            await bot.send(message)

        self.assertEqual(client.group_calls, 3)

    async def test_group_send_raises_after_retry_exhausted(self) -> None:
        bot = Bot(ws_url="ws://127.0.0.1:3001")
        client = _RetryingClient([TimeoutError(), TimeoutError(), TimeoutError()])
        bot._client = client  # type: ignore[assignment]
        message = BotMessage(
            message_id="m1",
            data_list=[{"type": "text", "data": {"text": "hello"}}],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with patch("napcat_adapter.bot.SEND_RETRY_DELAYS", (0, 0)):
            with self.assertRaisesRegex(RuntimeError, "failed after 3 attempts"):
                await bot.send(message)

        self.assertEqual(client.group_calls, 3)

    async def test_mixed_message_keeps_text_when_image_send_times_out(self) -> None:
        bot = Bot(ws_url="ws://127.0.0.1:3001")
        client = _RetryingClient(
            [
                {"message_id": 1},
                TimeoutError(),
                TimeoutError(),
                TimeoutError(),
                {"message_id": 2},
            ],
        )
        bot._client = client  # type: ignore[assignment]
        message = BotMessage(
            message_id="m1",
            data_list=[
                {"type": "text", "data": {"text": "before"}},
                {"type": "image", "data": {"file": "base64://cG5n"}},
                {"type": "text", "data": {"text": "after"}},
            ],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with patch("napcat_adapter.bot.SEND_RETRY_DELAYS", (0, 0)):
            await bot.send(message)

        self.assertEqual(client.group_calls, 5)
        self.assertEqual([len(batch) for batch in client.group_messages], [1, 1, 1, 1, 1])

    async def test_image_only_message_raises_when_image_send_times_out(self) -> None:
        bot = Bot(ws_url="ws://127.0.0.1:3001")
        client = _RetryingClient([TimeoutError(), TimeoutError(), TimeoutError()])
        bot._client = client  # type: ignore[assignment]
        message = BotMessage(
            message_id="m1",
            data_list=[{"type": "image", "data": {"file": "base64://cG5n"}}],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with patch("napcat_adapter.bot.SEND_RETRY_DELAYS", (0, 0)):
            with self.assertRaisesRegex(RuntimeError, "no sendable segments sent"):
                await bot.send(message)

        self.assertEqual(client.group_calls, 3)


class _RetryingClient:
    is_running = True

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.group_calls = 0
        self.private_calls = 0
        self.group_messages: list[list[object]] = []
        self.private_messages: list[list[object]] = []

    async def send_group_msg(self, *, group_id: str, message: list[object]) -> object:
        del group_id
        self.group_calls += 1
        self.group_messages.append(message)
        return self._next()

    async def send_private_msg(self, *, user_id: str, message: list[object]) -> object:
        del user_id
        self.private_calls += 1
        self.private_messages.append(message)
        return self._next()

    def _next(self) -> object:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class NapCatProtocolAdaptTest(unittest.TestCase):
    def test_onebot_raw_base64_image_uses_base64_uri_for_cq(self) -> None:
        payload = MessagePayload(
            message_id="m1",
            message_type="group",
            self_id="10001",
            group_id="12345",
            message=[
                ImageMessageSegment(
                    data=ImageSegmentData(
                        content="cG5n",
                        mime_type="image/png",
                        name="probe.png",
                    ),
                ),
            ],
        )

        message = onebot_to_bot(payload)

        self.assertEqual(message.data_list[0]["data"]["file"], "base64://cG5n")


if __name__ == "__main__":
    unittest.main()
