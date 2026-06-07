from __future__ import annotations

from hotmeme.models import ImageItem, ReviewStatus

DEFAULT_CN_TITLE_BLOCKLIST = frozenset(
    {
        "色情",
        "裸体",
        "赌博",
        "代孕",
        "刷单",
        "加微信",
        "私聊领取",
        "免费领取",
    },
)

DEFAULT_CN_RISK_KEYWORDS = frozenset(
    {
        "习近平",
        "六四",
        "台独",
        "港独",
    },
)


def filter_cn_risk_items(
    items: list[ImageItem],
    *,
    title_blocklist: frozenset[str] = DEFAULT_CN_TITLE_BLOCKLIST,
    risk_keywords: frozenset[str] = DEFAULT_CN_RISK_KEYWORDS,
    drop_rejected: bool = True,
) -> list[ImageItem]:
    """过滤广告引流、敏感词与已驳回项。"""
    kept: list[ImageItem] = []
    for item in items:
        if drop_rejected and item.review_status == ReviewStatus.REJECTED:
            continue
        title = item.title
        topic = item.topic or ""
        text = f"{title} {topic}"
        if any(word in text for word in title_blocklist):
            continue
        if any(word in text for word in risk_keywords):
            continue
        if "ad" in item.risk_flags or "spam" in item.risk_flags:
            continue
        kept.append(item)
    return kept
