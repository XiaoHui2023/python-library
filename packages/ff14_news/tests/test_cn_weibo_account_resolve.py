from crawl4weibo.models.user import User

from ff14_news.channels.cn_weibo.account_resolve import (
    is_official_account_key,
    pick_official_uid,
)
from ff14_news.channels.cn_weibo.constants import (
    DEFAULT_UID,
    OFFICIAL_DISPLAY_NAME,
    SCREEN_NAME,
)


def test_is_official_account_key() -> None:
    assert is_official_account_key(SCREEN_NAME)
    assert is_official_account_key(OFFICIAL_DISPLAY_NAME)
    assert is_official_account_key(DEFAULT_UID)
    assert not is_official_account_key("别的账号")


def test_pick_official_uid_prefers_known_uid() -> None:
    users = [
        User(id="999", screen_name="山寨最终幻想14"),
        User(id=DEFAULT_UID, screen_name=SCREEN_NAME),
    ]
    uid = pick_official_uid(users, query=OFFICIAL_DISPLAY_NAME)
    assert uid == DEFAULT_UID


def test_pick_official_uid_ignores_same_display_name_impostor() -> None:
    users = [
        User(id="999", screen_name=OFFICIAL_DISPLAY_NAME),
        User(id=DEFAULT_UID, screen_name=SCREEN_NAME),
    ]
    uid = pick_official_uid(users, query=OFFICIAL_DISPLAY_NAME)
    assert uid == DEFAULT_UID


def test_pick_official_uid_accepts_verified_display_name() -> None:
    users = [
        User(
            id=DEFAULT_UID,
            screen_name=OFFICIAL_DISPLAY_NAME,
            verified=True,
            verified_reason="《最终幻想14》官方微博",
        ),
    ]
    uid = pick_official_uid(users, query=OFFICIAL_DISPLAY_NAME)
    assert uid == DEFAULT_UID


def test_pick_official_uid_rejects_impostor_only() -> None:
    users = [User(id="999", screen_name=OFFICIAL_DISPLAY_NAME)]
    try:
        pick_official_uid(users, query=OFFICIAL_DISPLAY_NAME)
    except ValueError as exc:
        assert SCREEN_NAME in str(exc)
    else:
        raise AssertionError("expected ValueError")
