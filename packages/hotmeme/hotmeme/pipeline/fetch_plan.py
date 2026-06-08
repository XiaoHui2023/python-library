from __future__ import annotations

from hotmeme.models import DEFAULT_XHS_SEARCH_TAGS, XiaohongshuPolicy
from hotmeme.post_process import LOCAL_FILTER_CHAIN
from hotmeme.sources.parsers.xiaohongshu import format_xhs_tag_query

_DOUYIN_HOT = "GET /api/v1/douyin/web/fetch_hot_search_result (1 次)"
_DOUYIN_SEARCH = (
    "POST /api/v1/douyin/search/fetch_general_search_v2"
    " (热榜首词, sort_type=1, publish_time=1，1 次)"
)


def _xhs_tag_search_steps(policy: XiaohongshuPolicy) -> list[str]:
    keywords = policy.search_keywords()
    if not keywords:
        sample = format_xhs_tag_query(DEFAULT_XHS_SEARCH_TAGS[0])
        keywords = [sample]
    steps: list[str] = []
    for keyword in keywords:
        steps.append(
            "GET /api/v1/xiaohongshu/app_v2/search_notes"
            f" ({keyword}, page={policy.page}, sort_type={policy.sort_type},"
            f" time_filter={policy.time_filter}，1 次)"
        )
    return steps


_PLATFORM_STEPS_BUILDERS = {
    "douyin": lambda _xhs: [_DOUYIN_HOT, _DOUYIN_SEARCH],
    "xiaohongshu": _xhs_tag_search_steps,
}

_MIN_CALLS_BUILDERS = {
    "douyin": lambda _xhs: 2,
    "xiaohongshu": lambda xhs: xhs.tikhub_call_count(),
}

API_LAYER_FILTERS: dict[str, str] = {
    "douyin": "API: sort_type=1(综合), publish_time=1(一天内)；来源层 NSFW",
    "xiaohongshu": "API: tag 搜索 + sort_type + time_filter；来源层 NSFW",
}


def _xiaohongshu_policy(xiaohongshu: XiaohongshuPolicy | None) -> XiaohongshuPolicy:
    return xiaohongshu or XiaohongshuPolicy()


def describe_expected_api_calls(
    platforms: list[str],
    *,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> list[str]:
    """按平台列出计划中的 TikHub 请求（计费按次）。"""
    xhs = _xiaohongshu_policy(xiaohongshu)
    lines: list[str] = []
    for platform in platforms:
        builder = _PLATFORM_STEPS_BUILDERS.get(platform)
        if builder is None:
            lines.append(f"{platform}: 暂无 TikHub 工作流")
            continue
        for step in builder(xhs):
            lines.append(f"{platform}: {step}")
    return lines


def min_expected_call_count(
    platforms: list[str],
    *,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> int:
    """各平台最少请求次数之和。"""
    xhs = _xiaohongshu_policy(xiaohongshu)
    return sum(_MIN_CALLS_BUILDERS.get(platform, lambda _p: 0)(xhs) for platform in platforms)


def local_filter_chain() -> str:
    """本地后处理阶段（不在 TikHub 参数里）。"""
    return LOCAL_FILTER_CHAIN
