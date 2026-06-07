def normalize_proxy_url(value: str | None) -> str | None:
    """将 ``host:port`` 或完整 URL 规范为 ``http://…`` 代理地址。

    Args:
        value: 代理地址；空串或 None 表示不使用代理
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if "://" not in text:
        return f"http://{text}"
    return text
