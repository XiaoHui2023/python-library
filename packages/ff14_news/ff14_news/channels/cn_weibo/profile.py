def weibo_timeline_container_id(uid: str) -> str:
    """用户微博时间线 containerid（固定规则）。

    Args:
        uid: 微博 numeric uid
    """
    uid = str(uid).strip()
    if not uid:
        raise ValueError("uid must not be empty")
    return f"107603{uid}"
