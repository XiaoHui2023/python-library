from onebot_protocol import MessagePayload, TextMessageSegment, TextSegmentData


def _text_payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "message": [TextMessageSegment(data=TextSegmentData(text="hi"))],
    }
    base.update(overrides)
    return base


def test_empty_message_id_generates_uuid() -> None:
    payload = MessagePayload.model_validate(
        _text_payload(
            message_type="group",
            group_id="123",
            message_id="",
        ),
    )
    assert payload.message_id
    assert len(payload.message_id) >= 32


def test_onebot11_fields_passthrough() -> None:
    payload = MessagePayload.model_validate(
        {
            "message_type": "group",
            "self_id": 10001,
            "group_id": 20002,
            "user_id": 30003,
            "message": [TextMessageSegment(data=TextSegmentData(text="ping"))],
        },
    )
    assert payload.message_type == "group"
    assert payload.self_id == "10001"
    assert payload.group_id == "20002"
    assert payload.user_id == "30003"
    assert payload.peer_id == "20002"


def test_private_peer_is_user_id() -> None:
    payload = MessagePayload.model_validate(
        {
            "message_type": "private",
            "self_id": "10001",
            "user_id": "40004",
            "message": [TextMessageSegment(data=TextSegmentData(text="dm"))],
        },
    )
    assert payload.message_type == "private"
    assert payload.peer_id == "40004"


def test_legacy_field_aliases() -> None:
    payload = MessagePayload.model_validate(
        {
            "source_type": "group",
            "bot_id": "10001",
            "session_id": "20002",
            "messages": [TextMessageSegment(data=TextSegmentData(text="legacy"))],
        },
    )
    assert payload.message_type == "group"
    assert payload.self_id == "10001"
    assert payload.group_id == "20002"
    assert payload.message[0].data.text == "legacy"
