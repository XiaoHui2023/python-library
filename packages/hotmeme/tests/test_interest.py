from hotmeme.filter.interest import filter_low_interest_items, is_low_interest_title
from hotmeme.models import ImageItem, MediaType


def _item(title: str) -> ImageItem:
    return ImageItem(
        id="x:1",
        provider="tikhub",
        source_id="1",
        title=title,
        image_url="https://example.com/a.jpg",
        source_url="https://example.com/p",
        media_type=MediaType.IMAGE,
    )


def test_is_low_interest_birthday() -> None:
    assert is_low_interest_title("生日快乐我的伙计，祝你健康平安")
    assert filter_low_interest_items([_item("生日快乐")]) == []


def test_keeps_normal_hot_post() -> None:
    title = "49岁男子爬山失踪后续"
    assert not is_low_interest_title(title)
    assert len(filter_low_interest_items([_item(title)])) == 1
