from crawl4weibo.models.user import User

from ff14_news.channels.cn_weibo.constants import (
    DEFAULT_UID,
    OFFICIAL_DISPLAY_NAME,
    SCREEN_NAME,
)


def is_official_account_key(account_key: str) -> bool:
    """是否为已知的 FF14 官方微博标识。"""
    key = account_key.strip()
    if not key:
        return False
    if key == DEFAULT_UID:
        return True
    if key.lower() == SCREEN_NAME.lower():
        return True
    return key == OFFICIAL_DISPLAY_NAME


def pick_official_uid(users: list[User], *, query: str) -> str:
    """从用户搜索结果中选定 FF14 官方微博 uid（仅认 cnff14 / 官方 uid）。

    Args:
        users: crawl4weibo 用户搜索列表
        query: 原始查询词

    Raises:
        ValueError: 列表中找不到官方账号
    """
    if not users:
        raise ValueError(f"cannot resolve uid for account={query!r}")

    for user in users:
        if str(user.id) == DEFAULT_UID:
            return DEFAULT_UID

    for user in users:
        if user.screen_name.lower() == SCREEN_NAME.lower():
            return str(user.id)

    for user in users:
        if user.screen_name == OFFICIAL_DISPLAY_NAME and user.verified:
            reason = user.verified_reason or ""
            if "最终幻想14" in reason and "官方" in reason:
                return str(user.id)

    raise ValueError(
        f"cannot resolve official uid for account={query!r}; "
        f"expected screen_name={SCREEN_NAME!r} or uid={DEFAULT_UID}",
    )
