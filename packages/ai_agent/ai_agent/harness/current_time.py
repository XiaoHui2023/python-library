from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_current_time(timezone: str = "") -> str:
    """
    返回当前日期与时间。

    Args:
        timezone: IANA 时区名，如 Asia/Shanghai；留空则用本机本地时区

    Returns:
        ISO 8601 格式的时间字符串
    """
    if timezone.strip():
        try:
            tz = ZoneInfo(timezone.strip())
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"未知时区: {timezone}") from exc
        now = datetime.now(tz)
    else:
        now = datetime.now().astimezone()
    return now.isoformat(timespec="seconds")
