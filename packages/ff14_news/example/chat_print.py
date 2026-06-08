"""将 NewsFeedBundle 以聊天消息样式输出到终端（含头图）。"""
from __future__ import annotations

import urllib.error
import urllib.request
from io import BytesIO

from rich.console import Console, Group, RenderableType
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from textual_image.renderable import Image as TerminalImage

from ff14_news.channel_protocol import NewsChannel
from ff14_news.models import NewsArticle, NewsFeedBundle

_USER_AGENT = "Mozilla/5.0 (compatible; python-library-ff14-news-example/0.1)"
_PANEL_HORIZONTAL_PADDING = 6
_URL_UPGRADE_PAIRS = (
    ("/orj180/", "/orj1080/"),
    ("/orj360/", "/orj1080/"),
    ("/orj480/", "/orj1080/"),
    ("/thumbnail/", "/large/"),
    ("/bmiddle/", "/large/"),
    ("wap360", "large"),
    ("square", "large"),
)
_CHANNEL_BORDER: dict[str, str] = {
    "cn_official": "#61afef",
    "cn_weibo": "#e5c07b",
    "jp_official": "#98c379",
}
_THEME = Theme(
    {
        "chat.sender": "#abb2bf",
        "chat.time": "#5c6370",
        "chat.title": "#e5e5e5",
        "chat.summary": "#c8c8c8",
        "chat.link": "#61afef",
        "chat.error": "#e06c75",
        "chat.hint": "#5c6370",
    }
)


def make_console() -> Console:
    return Console(
        theme=_THEME,
        color_system="truecolor",
        force_terminal=True,
        legacy_windows=False,
    )


def print_feed_bundle(
    bundle: NewsFeedBundle,
    *,
    channels: dict[str, NewsChannel],
    channel_order: list[str],
    console: Console | None = None,
) -> None:
    """按渠道顺序打印聊天式消息流。"""
    out = console or make_console()
    ordered_ids = list(channel_order)
    for channel_id in bundle.feeds:
        if channel_id not in ordered_ids:
            ordered_ids.append(channel_id)
    for err in bundle.errors:
        if err.channel_id not in ordered_ids:
            ordered_ids.append(err.channel_id)

    for channel_id in ordered_ids:
        feed = bundle.feeds.get(channel_id)
        if feed is not None:
            display_name = channels[channel_id].display_name
            for article in feed.articles:
                out.print(
                    render_article_message(
                        article,
                        display_name,
                        channel_id,
                        console=out,
                    )
                )
        for err in bundle.errors:
            if err.channel_id != channel_id:
                continue
            label = channels.get(channel_id)
            name = label.display_name if label is not None else channel_id
            out.print(
                Panel(
                    Text(err.message, style="chat.error"),
                    title=f"[chat.sender]{escape(name)}[/]",
                    border_style=_CHANNEL_BORDER.get(channel_id, "#5c6370"),
                )
            )


def render_article_message(
    article: NewsArticle,
    display_name: str,
    channel_id: str,
    *,
    console: Console,
) -> RenderableType:
    """单篇文章的聊天气泡。"""
    time_text = article.publish_date.strftime("%Y-%m-%d %H:%M")
    header = Text.assemble(
        (display_name, "chat.sender"),
        ("  ", ""),
        (time_text, "chat.time"),
    )
    body_lines: list[RenderableType] = [
        Text(article.title, style="chat.title bold"),
    ]
    if article.summary:
        body_lines.append(Text(article.summary, style="chat.summary"))
    cover = render_cover_image(article.cover_image_url, console=console)
    if cover is not None:
        body_lines.append(cover)
    elif article.cover_image_url:
        body_lines.append(
            Text(f"头图：{article.cover_image_url}", style="chat.hint"),
        )
    body_lines.append(Text(article.source_page_url, style="chat.link underline"))
    border = _CHANNEL_BORDER.get(channel_id, "#5c6370")
    return Panel(
        Group(*body_lines),
        title=header,
        border_style=border,
        padding=(0, 1),
    )


def render_cover_image(url: str | None, *, console: Console) -> RenderableType | None:
    if not url:
        return None
    display_url = upgrade_display_image_url(url)
    data = download_image_bytes(display_url)
    if data is None and display_url != url:
        data = download_image_bytes(url)
    if data is None:
        return None
    try:
        cell_width = max(48, console.width - _PANEL_HORIZONTAL_PADDING)
        return TerminalImage(
            BytesIO(data),
            width=cell_width,
            height="auto",
        )
    except Exception:
        return None


def upgrade_display_image_url(url: str) -> str:
    """展示用：把常见缩略图 CDN 路径换成更大图。"""
    for small, large in _URL_UPGRADE_PAIRS:
        if small in url:
            return url.replace(small, large, 1)
    return url


def download_image_bytes(url: str) -> bytes | None:
    headers: dict[str, str] = {"User-Agent": _USER_AGENT}
    if "sinaimg.cn" in url or "weibocdn.com" in url:
        headers["Referer"] = "https://m.weibo.cn/"
    request = urllib.request.Request(url, headers=headers)
    try:
        return urllib.request.urlopen(request, timeout=120).read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
