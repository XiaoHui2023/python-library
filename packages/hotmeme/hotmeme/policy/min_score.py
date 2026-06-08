from __future__ import annotations

from hotmeme.models import XiaohongshuPolicy


def resolve_platform_min_scores(
    platforms: list[str],
    *,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> dict[str, float]:
    """根据管线平台列表与各平台策略，汇总后处理用的最低互动分。"""
    scores: dict[str, float] = {}
    if "xiaohongshu" in platforms:
        policy = xiaohongshu if xiaohongshu is not None else XiaohongshuPolicy()
        scores["xiaohongshu"] = policy.min_score
    return scores
