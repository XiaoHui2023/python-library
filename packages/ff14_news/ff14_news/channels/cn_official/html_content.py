from ff14_news.channels.cn_official.constants import HTML_BASE_URL
from ff14_news.common.html_blocks import html_to_blocks as _html_to_blocks
from ff14_news.models import NewsContentBlock


def html_to_blocks(
    html: str,
    *,
    base_url: str = HTML_BASE_URL,
) -> list[NewsContentBlock]:
    return _html_to_blocks(html, base_url=base_url)
