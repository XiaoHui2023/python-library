from hotmeme.models import FetchDiagnostics, ImageItem, MediaType, XhsKeywordFetchStat
from hotmeme.pipeline.diagnostics import format_fetch_diagnostics, post_process_traced


def _item(title: str, *, image_url: str = "https://example.com/a.jpg") -> ImageItem:
    return ImageItem(
        id=f"id:{title}",
        provider="tikhub",
        source_id=title,
        title=title,
        image_url=image_url,
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )


def test_post_process_traced_records_drops() -> None:
    items = [
        _item("有图", image_url="https://example.com/a.jpg"),
        _item("无图", image_url=""),
        _item("早安祝福", image_url="https://example.com/b.jpg"),
    ]
    processed, stages = post_process_traced(items, allow_nsfw=False)
    assert len(processed) == 2
    displayable = next(stage for stage in stages if stage.stage == "displayable")
    assert displayable.dropped == 1


def test_format_fetch_diagnostics_includes_keyword_row() -> None:
    diag = FetchDiagnostics(
        parsed_before_filter=2,
        final_count=1,
        xhs_keywords=[
            XhsKeywordFetchStat(
                keyword="#搞笑#",
                search_tag="搞笑",
                api_list_items=20,
                note_candidates=18,
                parsed_with_media=2,
                no_media=16,
                tag_dedup_skipped=0,
                merged_items=2,
            ),
        ],
    )
    text = "\n".join(format_fetch_diagnostics(diag))
    assert "API items=20" in text
    assert "无封面=16" in text
