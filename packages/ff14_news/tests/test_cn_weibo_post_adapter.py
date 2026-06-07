from datetime import datetime, timezone

from crawl4weibo.models.post import Post

from ff14_news.channels.cn_weibo.post_adapter import post_to_list_item


def test_post_to_list_item_uses_plain_text() -> None:
    post = Post(
        id="123",
        bid="abc",
        user_id="1784473157",
        text="测试标题行\n第二行",
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        pic_urls=["https://example.com/a.jpg"],
    )
    item = post_to_list_item(post, channel_id="cn_weibo")
    assert item.id == "123"
    assert item.title == "测试标题行"
    assert item.summary.startswith("测试标题行")
    assert item.cover_image_url == "https://example.com/a.jpg"
