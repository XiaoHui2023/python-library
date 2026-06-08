from hotmeme.filter.min_score import filter_min_score_items
from hotmeme.models import ImageItem, MediaType
from hotmeme.pipeline.diagnostics import post_process_traced
from hotmeme.policy.min_score import resolve_platform_min_scores


def _item(
    *,
    community: str = "xiaohongshu",
    score: float | None = 600.0,
    title: str = "热帖",
) -> ImageItem:
    return ImageItem(
        id=f"id:{community}:{score}:{title}",
        provider="tikhub",
        source_id=title,
        title=title,
        image_url="https://example.com/a.jpg",
        source_url="https://example.com/p",
        community=community,
        score=score,
        media_type=MediaType.IMAGE,
    )


def test_filter_min_score_drops_at_or_below_threshold() -> None:
    items = [
        _item(score=500.0),
        _item(score=501.0, title="过线"),
        _item(score=None, title="无分"),
    ]
    kept = filter_min_score_items(
        items,
        platform_min_scores={"xiaohongshu": 500.0},
    )
    assert [item.title for item in kept] == ["过线"]


def test_resolve_platform_min_scores_uses_defaults() -> None:
    scores = resolve_platform_min_scores(["xiaohongshu"])
    assert scores == {"xiaohongshu": 500.0}


def test_post_process_traced_records_min_score_drops() -> None:
    items = [
        _item(score=100.0, title="低分"),
        _item(score=800.0, title="高分"),
    ]
    processed, stages = post_process_traced(
        items,
        allow_nsfw=False,
        platform_min_scores={"xiaohongshu": 500.0},
    )
    assert len(processed) == 1
    assert processed[0].title == "高分"
    min_score = next(stage for stage in stages if stage.stage == "min_score")
    assert min_score.dropped == 1
