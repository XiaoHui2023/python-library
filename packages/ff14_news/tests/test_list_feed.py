from ff14_news.common.list_feed import article_from_list_item
from ff14_news.models import NewsListItem


def test_article_from_list_item_empty_blocks() -> None:
    from datetime import datetime, timezone

    item = NewsListItem(
        channel_id="cn_official",
        id="1",
        title="t",
        publish_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        summary="s",
        cover_image_url="https://example.com/c.jpg",
        source_page_url="https://example.com/1",
    )
    article = article_from_list_item(item, category_code=5310)
    assert article.blocks == []
    assert article.category_code == 5310
    assert article.title == "t"
