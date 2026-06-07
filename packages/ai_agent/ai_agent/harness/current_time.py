from __future__ import annotations

from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_UTC_ALIASES = frozenset({"UTC", "Etc/UTC", "Z"})


def get_current_time(timezone: str = "") -> str:
    """
    返回当前日期与时间。

    Args:
        timezone: IANA 时区名，如 Asia/Shanghai；留空则用本机本地时区

    Returns:
        ISO 8601 格式的时间字符串
    """
    if timezone.strip():
        tz_name = timezone.strip()
        if tz_name in _UTC_ALIASES:
            now = datetime.now(dt_timezone.utc)
        else:
            try:
                tz = ZoneInfo(tz_name)
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"未知时区: {timezone}") from exc
            now = datetime.now(tz)
    else:
        now = datetime.now().astimezone()
    return now.isoformat(timespec="seconds")
