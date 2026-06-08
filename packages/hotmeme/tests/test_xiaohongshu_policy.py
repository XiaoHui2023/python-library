from unittest.mock import MagicMock, patch

from hotmeme.models import ImageItem, MediaType, XiaohongshuPolicy
from hotmeme.pipeline.fetch_plan import min_expected_call_count
from hotmeme.sources.platforms.xiaohongshu import XiaohongshuWorkflow


def test_search_keywords_tags_disabled_uses_first_tag_only() -> None:
    policy = XiaohongshuPolicy(
        tags_enabled=False,
        search_tags=["搞笑", "段子"],
    )
    assert policy.search_keywords() == ["#搞笑#"]
    assert policy.tikhub_call_count() == 1


def test_search_keywords_tags_enabled_uses_all_tags() -> None:
    policy = XiaohongshuPolicy(
        tags_enabled=True,
        search_tags=["搞笑", "段子"],
    )
    assert policy.search_keywords() == ["#搞笑#", "#段子#"]
    assert policy.tikhub_call_count() == 2


def test_min_expected_call_count_matches_enabled_tags() -> None:
    policy = XiaohongshuPolicy(tags_enabled=True, search_tags=["搞笑", "段子"])
    assert min_expected_call_count(["xiaohongshu"], xiaohongshu=policy) == 2


def _image_item() -> ImageItem:
    return ImageItem(
        id="tikhub:xhs:1",
        provider="tikhub",
        source_id="1",
        title="搞笑帖",
        image_url="https://example.com/a.jpg",
        source_url="https://www.xiaohongshu.com/explore/1",
        community="xiaohongshu",
        media_type=MediaType.IMAGE,
    )


@patch("hotmeme.sources.platforms.xiaohongshu.parse_xhs_search_notes", return_value=[_image_item()])
def test_workflow_sets_search_tag_on_items(mock_parse) -> None:
    client = MagicMock()
    policy = XiaohongshuPolicy(tags_enabled=False, search_tags=["搞笑"])
    items = XiaohongshuWorkflow(policy).fetch(client)
    assert len(items) == 1
    assert items[0].search_tag == "搞笑"


@patch("hotmeme.sources.platforms.xiaohongshu.parse_xhs_search_notes", return_value=[_image_item()])
def test_workflow_passes_page_sort_and_time_filter(mock_parse) -> None:
    client = MagicMock()
    policy = XiaohongshuPolicy(
        tags_enabled=False,
        page=1,
        sort_type="popularity_descending",
        time_filter="一天内",
    )
    XiaohongshuWorkflow(policy).fetch(client)
    params = client.get.call_args.args[1]
    assert params["page"] == 1
    assert params["sort_type"] == "popularity_descending"
    assert params["time_filter"] == "一天内"
    assert params["keyword"] == "#搞笑#"
