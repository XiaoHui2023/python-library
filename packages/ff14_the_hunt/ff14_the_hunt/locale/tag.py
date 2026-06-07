from __future__ import annotations

from enum import Enum


class HuntDisplayLocale(str, Enum):
    """导出 JSON 与终端展示所用的语言。"""

    ZH = "zh"
    EN = "en"
