import unittest

from onebot_protocol import ImageMessageSegment, MessagePayload, TextMessageSegment

from qq_adapter.bot import QQBot
from qq_adapter.models import QQMediaAttachment, QQMessage, QQSource
from qq_adapter.protocol_adapter import onebot_to_qq


class ProtocolMediaTests(unittest.TestCase):
    def test_onebot_image_base64_becomes_qq_media(self) -> None:
        payload = MessagePayload(
            message_id="m1",
            message_type="group",
            self_id="bot",
            group_id="group1",
            user_id="user1",
            message=[
                TextMessageSegment(data={"text": "before"}),
                ImageMessageSegment(
                    data={
                        "content": "cG5n",
                        "mime_type": "image/png",
                        "name": "probe.png",
                    },
                ),
                TextMessageSegment(data={"text": "after"}),
            ],
        )

        msg = onebot_to_qq(payload)

        self.assertEqual(msg.source_type, QQSource.GROUP)
        self.assertEqual(msg.content, "beforeafter")
        self.assertEqual(len(msg.media), 1)
        self.assertEqual(msg.media[0].file_type, 1)
        self.assertEqual(msg.media[0].file_data, "cG5n")
        self.assertEqual(msg.media[0].mime_type, "image/png")

    def test_onebot_image_url_becomes_qq_media_url(self) -> None:
        payload = MessagePayload(
            message_id="m1",
            message_type="group",
            self_id="bot",
            group_id="group1",
            message=[
                ImageMessageSegment(
                    data={"content": "https://example.com/a.png"},
                ),
            ],
        )

        msg = onebot_to_qq(payload)

        self.assertEqual(msg.media[0].url, "https://example.com/a.png")
        self.assertEqual(msg.media[0].file_data, "")


class RecordingBot(QQBot):
    def __init__(self) -> None:
        super().__init__("app", "secret", "bot")
        self.calls: list[tuple[str, dict]] = []

    async def _api_post(self, path: str, body: dict) -> dict:
        self.calls.append((path, body))
        if path.endswith("/files"):
            return {"file_info": "media-token"}
        return {"id": "sent"}


class BotMediaSendTests(unittest.IsolatedAsyncioTestCase):
    async def test_group_image_uses_upload_then_media_message(self) -> None:
        bot = RecordingBot()
        msg = QQMessage(
            source_type=QQSource.GROUP,
            source_id="group-openid",
            session_id="group-openid",
            msg_id="msg1",
            content="hello",
            media=[QQMediaAttachment(file_type=1, file_data="cG5n")],
        )

        await bot.send_message(msg)

        self.assertEqual(bot.calls[0][0], "/v2/groups/group-openid/files")
        self.assertEqual(
            bot.calls[0][1],
            {"file_type": 1, "srv_send_msg": False, "file_data": "cG5n"},
        )
        self.assertEqual(bot.calls[1][0], "/v2/groups/group-openid/messages")
        self.assertEqual(bot.calls[1][1]["msg_type"], 7)
        self.assertEqual(bot.calls[1][1]["content"], "hello")
        self.assertEqual(bot.calls[1][1]["media"], {"file_info": "media-token"})

    async def test_media_upload_failure_falls_back_to_text(self) -> None:
        bot = RecordingBot()
        msg = QQMessage(
            source_type=QQSource.GROUP,
            source_id="group-openid",
            session_id="group-openid",
            msg_id="msg1",
            content="hello",
            media=[QQMediaAttachment(file_type=1, file_data="cG5n")],
        )

        async def fail_upload(path: str, body: dict) -> dict:
            bot.calls.append((path, body))
            return {} if path.endswith("/files") else {"id": "sent"}

        bot._api_post = fail_upload  # type: ignore[method-assign]

        await bot.send_message(msg)

        self.assertEqual(bot.calls[1][0], "/v2/groups/group-openid/messages")
        self.assertEqual(bot.calls[1][1]["msg_type"], 0)
        self.assertEqual(bot.calls[1][1]["content"], "hello")

    async def test_unknown_source_without_explicit_type_raises(self) -> None:
        bot = RecordingBot()
        msg = QQMessage(
            source_id="unknown",
            session_id="unknown",
            msg_id="msg1",
            content="hello",
        )

        with self.assertRaisesRegex(RuntimeError, "未知的 QQ 消息来源"):
            await bot.send_message(msg)


if __name__ == "__main__":
    unittest.main()
