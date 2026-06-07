from ff14_news.models import NewsArticle, NewsListItem


def article_from_list_item(
    item: NewsListItem,
    *,
    category_code: int | None = None,
) -> NewsArticle:
    """列表项转文章：保留列表级字段，正文块为空。"""
    return NewsArticle(
        channel_id=item.channel_id,
        id=item.id,
        title=item.title,
        publish_date=item.publish_date,
        summary=item.summary,
        category_code=category_code,
        cover_image_url=item.cover_image_url,
        source_page_url=item.source_page_url,
        blocks=[],
    )
