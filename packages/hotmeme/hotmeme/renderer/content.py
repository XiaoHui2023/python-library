from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from hotmeme.models import ImageItem, MediaType


class ContentBlockKind(StrEnum):
    """帖子内容块种类。"""

    IMAGE = "image"
    TEXT = "text"
    VIDEO = "video"


class PostContentBlock(BaseModel):
    """单块可展示内容：图片二进制、文或视频。"""

    model_config = ConfigDict(extra="forbid")

    kind: ContentBlockKind = Field(description="内容块类型")
    data: bytes | None = Field(default=None, description="已下载图片的二进制数据")
    content_type: str | None = Field(default=None, description="图片 MIME，如 image/jpeg")
    url: str | None = Field(default=None, description="视频或未下载图片的远程地址")
    text: str | None = Field(default=None, description="正文段落")


class PostContent(BaseModel):
    """单条消息正文：先图后文，多图与文字块同属一条交付。"""

    model_config = ConfigDict(extra="forbid")

    blocks: list[PostContentBlock] = Field(
        default_factory=list,
        description="先图后文；同一 PostContent 对应一条对外消息",
    )


class PostReference(BaseModel):
    """原帖参考信息，不属于正文内容。"""

    model_config = ConfigDict(extra="forbid")

    author: str | None = Field(default=None, description="作者昵称")
    source_url: str = Field(description="原帖页面链接")
    search_tag: str | None = Field(default=None, description="拉取时使用的搜索话题 tag")
    image_source_urls: list[str] = Field(
        default_factory=list,
        description="远程图片 URL，仅供溯源",
    )


def compose_post_text(item: ImageItem) -> str:
    """把标题与正文合并为一段展示文本，避免重复行。"""
    title = item.title.strip()
    body = (item.body or "").strip()
    if not body:
        return title
    if not title or title == body:
        return body
    if body.startswith(title):
        return body
    if title in body:
        return body
    return f"{title}\n\n{body}"


def _remote_image_urls(item: ImageItem) -> list[str]:
    if item.image_urls:
        return list(item.image_urls)
    if item.image_url and not item.image_blobs:
        return [item.image_url]
    return []


def _limited_image_urls(item: ImageItem, max_images_per_item: int | None) -> list[str]:
    urls = _remote_image_urls(item)
    if max_images_per_item is not None:
        return urls[:max_images_per_item]
    return urls


def build_post_content(
    item: ImageItem,
    *,
    media_url: str,
    max_images_per_item: int | None = None,
) -> PostContent:
    """按平台约定把热帖项排成单条消息：先图后文。"""
    blocks: list[PostContentBlock] = []
    if item.media_type == MediaType.VIDEO and item.video_url:
        blocks.append(PostContentBlock(kind=ContentBlockKind.VIDEO, url=media_url))
    elif item.image_blobs:
        blobs = item.image_blobs
        if max_images_per_item is not None:
            blobs = blobs[:max_images_per_item]
        for blob in blobs:
            blocks.append(
                PostContentBlock(
                    kind=ContentBlockKind.IMAGE,
                    data=blob.data,
                    content_type=blob.content_type,
                ),
            )
    else:
        for url in _limited_image_urls(item, max_images_per_item):
            blocks.append(PostContentBlock(kind=ContentBlockKind.IMAGE, url=url))
    text = compose_post_text(item)
    if text.strip():
        blocks.append(PostContentBlock(kind=ContentBlockKind.TEXT, text=text))
    return PostContent(blocks=blocks)


def build_post_reference(
    item: ImageItem,
    *,
    max_images_per_item: int | None = None,
) -> PostReference:
    """提取作者与原帖链等参考字段。"""
    return PostReference(
        author=item.author,
        source_url=item.source_url,
        search_tag=item.search_tag,
        image_source_urls=_limited_image_urls(item, max_images_per_item),
    )
