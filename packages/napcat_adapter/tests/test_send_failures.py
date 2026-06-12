import unittest

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
