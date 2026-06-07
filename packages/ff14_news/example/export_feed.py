"""将 NewsFeed 写入目录：JSON + Markdown，仅下载头图。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ff14_news.models import NewsArticle, NewsFeed

_USER_AGENT = "Mozilla/5.0 (compatible; python-library-ff14-news-example/0.1)"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}


def export_feed_to_directory(feed: NewsFeed, output_dir: Path) -> Path:
    """抓取结果落盘；返回输出根目录。"""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    feed_summary: dict[str, Any] = {
        "channel_id": feed.channel_id,
        "source_list_url": feed.source_list_url,
        "category_code": feed.category_code,
        "fetched_at": feed.fetched_at.isoformat(),
        "articles": [],
    }

    for article in feed.articles:
        article_summary = write_article_bundle(article, output_dir)
        feed_summary["articles"].append(article_summary)

    feed_path = output_dir / "feed.json"
    feed_path.write_text(
        json.dumps(feed_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_dir


def write_article_bundle(article: NewsArticle, output_root: Path) -> dict[str, Any]:
    article_dir = output_root / str(article.id)
    images_dir = article_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    url_cache: dict[str, str] = {}
    cover_local: str | None = None
    if article.cover_image_url:
        cover_local = download_image(
            article.cover_image_url,
            images_dir,
            "cover",
            url_cache,
        )

    article_doc = {
        "channel_id": article.channel_id,
        "id": article.id,
        "title": article.title,
        "publish_date": article.publish_date.isoformat(),
        "summary": article.summary,
        "category_code": article.category_code,
        "source_page_url": article.source_page_url,
        "cover_image_source_url": article.cover_image_url,
        "cover_image_local_path": cover_local,
    }

    json_path = article_dir / "article.json"
    json_path.write_text(
        json.dumps(article_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    md_path = article_dir / "article.md"
    md_path.write_text(
        render_article_markdown(article, cover_local),
        encoding="utf-8",
    )

    return {
        "id": article.id,
        "title": article.title,
        "publish_date": article.publish_date.isoformat(),
        "directory": str(article_dir.relative_to(output_root)).replace("\\", "/"),
        "json": str(json_path.relative_to(output_root)).replace("\\", "/"),
        "markdown": str(md_path.relative_to(output_root)).replace("\\", "/"),
    }


def download_image(
    url: str,
    images_dir: Path,
    stem: str,
    url_cache: dict[str, str],
) -> str:
    if url in url_cache:
        return url_cache[url]
    ext = guess_image_suffix(url)
    filename = f"{stem}{ext}"
    dest = images_dir / filename
    headers = {"User-Agent": _USER_AGENT}
    if "sinaimg.cn" in url or "weibocdn.com" in url:
        headers["Referer"] = "https://m.weibo.cn/"
    request = urllib.request.Request(url, headers=headers)
    try:
        data = urllib.request.urlopen(request, timeout=120).read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"download failed HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"download failed: {url}") from exc
    dest.write_bytes(data)
    rel = f"images/{filename}"
    url_cache[url] = rel
    return rel


def guess_image_suffix(url: str) -> str:
    path = urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in _IMAGE_SUFFIXES:
        return suffix
    return ".jpg"


def render_article_markdown(
    article: NewsArticle,
    cover_local: str | None,
) -> str:
    lines = [
        f"# {article.title}",
        "",
        f"- 发布时间：{article.publish_date.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 摘要：{article.summary or '（无）'}",
        f"- 原文：{article.source_page_url}",
        "",
    ]
    if cover_local:
        lines.extend([f"![cover]({cover_local})", ""])
    return "\n".join(lines).rstrip() + "\n"
