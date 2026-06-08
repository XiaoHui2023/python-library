from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.filter import (
    dedup_items,
    filter_displayable_media,
    filter_low_interest_items,
    filter_nsfw_items,
    filter_risk_items,
)
from hotmeme.merge.rank import sort_items
from hotmeme.models import ImageItem


class PostProcessStageStat(BaseModel):
    """单步后处理进出条数。"""

    model_config = ConfigDict(extra="forbid")

    stage: str = Field(description="阶段名")
    in_count: int = Field(description="进入条数")
    out_count: int = Field(description="离开条数")
    dropped: int = Field(description="丢弃条数")


class XhsKeywordFetchStat(BaseModel):
    """单次小红书 tag 搜索的解析统计。"""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(description="搜索关键词，如 #搞笑#")
    search_tag: str = Field(description="话题 tag 名")
    api_list_items: int = Field(description="响应 data.items 列表长度")
    note_candidates: int = Field(description="识别到的笔记卡片数")
    parsed_with_media: int = Field(description="解析出可展示媒体的条数")
    no_media: int = Field(description="有笔记但无封面/视频 URL")
    tag_dedup_skipped: int = Field(description="跨 tag 合并时因 note id 重复跳过")
    merged_items: int = Field(description="本 keyword 新并入条数")


class FetchDiagnostics(BaseModel):
    """一轮拉取：解析与过滤诊断。"""

    model_config = ConfigDict(extra="forbid")

    parsed_before_filter: int = Field(default=0, description="进入 post_process 前条数")
    final_count: int = Field(default=0, description="post_process 后条数")
    xhs_keywords: list[XhsKeywordFetchStat] = Field(default_factory=list)
    post_process: list[PostProcessStageStat] = Field(default_factory=list)


def post_process_traced(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
) -> tuple[list[ImageItem], list[PostProcessStageStat]]:
    """热帖聚合后处理，并记录每步丢弃条数。"""
    stages: list[PostProcessStageStat] = []
    current = items

    def _step(name: str, fn) -> None:
        nonlocal current
        before = len(current)
        current = fn(current)
        stages.append(
            PostProcessStageStat(
                stage=name,
                in_count=before,
                out_count=len(current),
                dropped=before - len(current),
            ),
        )

    _step("displayable", filter_displayable_media)
    _step("nsfw", lambda batch: filter_nsfw_items(batch, allow_nsfw=allow_nsfw))
    _step("risk", filter_risk_items)
    _step("low_interest", filter_low_interest_items)
    _step("dedup", dedup_items)
    _step("rank", sort_items)
    return current, stages


def format_fetch_diagnostics(diagnostics: FetchDiagnostics) -> list[str]:
    """格式化为可打印的诊断行。"""
    lines = ["=== 拉取诊断 ==="]
    if diagnostics.xhs_keywords:
        lines.append("小红书（按 keyword）:")
        for row in diagnostics.xhs_keywords:
            lines.append(
                f"  {row.keyword}: API items={row.api_list_items}, "
                f"笔记候选={row.note_candidates}, 解析出图={row.parsed_with_media}, "
                f"无封面={row.no_media}, tag 去重跳过={row.tag_dedup_skipped}, "
                f"新并入={row.merged_items}",
            )
        api_total = sum(row.api_list_items for row in diagnostics.xhs_keywords)
        no_media_total = sum(row.no_media for row in diagnostics.xhs_keywords)
        if api_total > 0 and no_media_total >= api_total * 0.5:
            lines.append(
                "  提示: 无封面占比高时多为解析字段与 API 响应不一致（解析问题）",
            )
    lines.append(f"解析合计（过滤前）: {diagnostics.parsed_before_filter}")
    if diagnostics.post_process:
        lines.append("本地后处理:")
        for stage in diagnostics.post_process:
            lines.append(
                f"  {stage.stage}: {stage.in_count} → {stage.out_count} "
                f"(丢弃 {stage.dropped})",
            )
    lines.append(f"最终条数: {diagnostics.final_count}")
    if (
        diagnostics.xhs_keywords
        and diagnostics.parsed_before_filter == 0
        and any(row.api_list_items > 0 for row in diagnostics.xhs_keywords)
    ):
        lines.append("  提示: API 有 items 但解析为 0，优先查解析器")
    elif (
        diagnostics.parsed_before_filter > 0
        and diagnostics.final_count == 0
        and diagnostics.post_process
    ):
        lines.append("  提示: 解析有条目但过滤后为空，优先查 post_process 各阶段")
    lines.append("")
    return lines
