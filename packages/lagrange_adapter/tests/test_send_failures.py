import unittest

from lagrange_adapter.bot import Bot
from lagrange_adapter.models import BotMessage, MessageType


class LagrangeSendFailuresTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_raises_when_bot_is_not_running(self) -> None:
        bot = Bot(port=6199)
        message = BotMessage(
            message_id="m1",
            data_list=[{"type": "text", "data": {"text": "hello"}}],
            message_type=MessageType.GROUP,
            bot_id="10001",
            session_id="12345",
            user_name="u1",
        )

        with self.assertRaisesRegex(RuntimeError, "not running"):
            await bot.send(message)


if __name__ == "__main__":
    unittest.main()
