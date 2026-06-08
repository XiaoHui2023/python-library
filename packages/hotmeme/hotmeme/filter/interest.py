from __future__ import annotations

from hotmeme.models import ImageItem

_LOW_INTEREST_PHRASES = frozenset(
    {
        "生日快乐",
        "节日快乐",
        "周年快乐",
        "新婚快乐",
        "考试顺利",
        "早安",
        "晚安",
        "早上好",
        "晚上好",
    },
)


def is_low_interest_title(title: str) -> bool:
    """标题是否像祝福/打卡类社交帖（非热梗向）。"""
    text = title.strip()
    if not text:
        return False
    if any(phrase in text for phrase in _LOW_INTEREST_PHRASES):
        return True
    if "祝你" in text and "快乐" in text:
        return True
    return False


def filter_low_interest_items(items: list[ImageItem]) -> list[ImageItem]:
    """丢弃低趣味社交向标题的条目。"""
    return [item for item in items if not is_low_interest_title(item.title)]
