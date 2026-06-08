from __future__ import annotations

from typing import TYPE_CHECKING

from hotmeme.filter import (
    dedup_items,
    filter_displayable_media,
    filter_media_types,
    filter_min_score_items,
    filter_nsfw_items,
    filter_risk_items,
)
from hotmeme.models import MediaType
from hotmeme.merge.rank import sort_items
from hotmeme.models import FetchDiagnostics, ImageItem, PostProcessStageStat

if TYPE_CHECKING:
    from hotmeme.renderer.models import MemeOutputBatch


def post_process_traced(
    items: list[ImageItem],
    *,
    allow_nsfw: bool,
    media_types: list[MediaType] | None = None,
    platform_min_scores: dict[str, float] | None = None,
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
    _step(
        "media_types",
        lambda batch: filter_media_types(batch, allowed=media_types),
    )
    _step("nsfw", lambda batch: filter_nsfw_items(batch, allow_nsfw=allow_nsfw))
    _step("risk", filter_risk_items)
    min_scores = platform_min_scores or {}
    _step(
        "min_score",
        lambda batch: filter_min_score_items(
            batch,
            platform_min_scores=min_scores,
        ),
    )
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
        min_score_stage = next(
            (stage for stage in diagnostics.post_process if stage.stage == "min_score"),
            None,
        )
        if (
            min_score_stage is not None
            and min_score_stage.in_count > 0
            and min_score_stage.out_count == 0
        ):
            lines.append(
                "  提示: min_score 丢弃全部时常见原因为 score 未解析（互动数在 items 外层）",
            )
    lines.append("")
    return lines


def format_materialize_diagnostics(batch: MemeOutputBatch) -> list[str]:
    """格式化渲染前图片下载诊断行。"""
    stage = batch.materialize_stage
    errors = batch.materialize_errors
    if stage is None and not errors:
        return []
    lines = ["=== 图片下载（渲染前）==="]
    if stage is not None:
        lines.append(
            f"  materialize: {stage.in_count} → {stage.out_count} "
            f"(丢弃 {stage.dropped})",
        )
    for err in errors:
        lines.append(f"  {err}")
    lines.append("")
    return lines
