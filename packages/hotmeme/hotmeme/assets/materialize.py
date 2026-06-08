from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from hotmeme.assets.download import ImageDownloadError, download_image, item_image_source_urls
from hotmeme.models import AssetsPolicy, ImageBlob, ImageItem, PostProcessStageStat

ProgressCallback = Callable[[str], None]


def _format_download_error(item: ImageItem, index: int, total: int, url: str, exc: Exception) -> str:
    platform = item.community or "unknown"
    return (
        f"[{platform}] {item.source_id}: 图片 {index}/{total} 下载失败: {url} — {exc}"
    )


def _emit_progress(on_progress: ProgressCallback | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)


def _download_urls(item: ImageItem, policy: AssetsPolicy) -> list[str]:
    urls = item_image_source_urls(item)
    limit = policy.max_images_per_item
    if limit is not None:
        return urls[:limit]
    return urls


def _download_one_image(
    index: int,
    url: str,
    *,
    total: int,
    policy: AssetsPolicy,
    on_progress: ProgressCallback | None,
) -> tuple[int, ImageBlob | None, str | None, ImageDownloadError | None]:
    display_index = index + 1
    _emit_progress(on_progress, f"  图片 {display_index}/{total} 下载中…")
    try:
        blob = download_image(
            url,
            timeout=policy.timeout,
            min_bytes=policy.min_bytes,
        )
    except ImageDownloadError as exc:
        return index, None, url, exc
    _emit_progress(
        on_progress,
        f"  图片 {display_index}/{total} 完成（{len(blob.data)} 字节）",
    )
    return index, blob, url, None


def _download_images_parallel(
    urls: list[str],
    *,
    policy: AssetsPolicy,
    on_progress: ProgressCallback | None,
) -> tuple[list[ImageBlob] | None, tuple[int, str, ImageDownloadError] | None]:
    total = len(urls)
    if total == 0:
        return [], None
    if total == 1:
        _index, blob, url, exc = _download_one_image(
            0,
            urls[0],
            total=total,
            policy=policy,
            on_progress=on_progress,
        )
        if exc is not None:
            return None, (0, url or urls[0], exc)
        if blob is None:
            return None, (0, urls[0], ImageDownloadError("未知错误"))
        return [blob], None

    workers = min(policy.download_workers, total)
    blobs: list[ImageBlob | None] = [None] * total
    failures: list[tuple[int, str, ImageDownloadError]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _download_one_image,
                index,
                url,
                total=total,
                policy=policy,
                on_progress=on_progress,
            )
            for index, url in enumerate(urls)
        ]
        for future in as_completed(futures):
            index, blob, url, exc = future.result()
            if exc is not None:
                failures.append((index, url or urls[index], exc))
                continue
            blobs[index] = blob

    if failures:
        first_index, url, exc = min(failures, key=lambda row: row[0])
        return None, (first_index, url, exc)
    if any(blob is None for blob in blobs):
        missing = next(index for index, blob in enumerate(blobs) if blob is None)
        return None, (missing, urls[missing], ImageDownloadError("未知错误"))
    return [blob for blob in blobs if blob is not None], None


def materialize_item_images(
    item: ImageItem,
    *,
    policy: AssetsPolicy,
    on_progress: ProgressCallback | None = None,
) -> tuple[ImageItem | None, str | None]:
    """下载帖子图片到内存；任一张失败则丢弃该帖。"""
    urls = _download_urls(item, policy)
    if not urls:
        platform = item.community or "unknown"
        return None, f"[{platform}] {item.source_id}: 无图片 URL，无法下载"

    total = len(urls)
    blobs, failure = _download_images_parallel(
        urls,
        policy=policy,
        on_progress=on_progress,
    )
    if failure is not None:
        fail_index, url, exc = failure
        return None, _format_download_error(item, fail_index + 1, total, url, exc)
    if blobs is None:
        return None, f"[{item.community or 'unknown'}] {item.source_id}: 下载失败"

    primary_url = urls[0]
    return item.model_copy(
        update={
            "image_blobs": blobs,
            "image_urls": urls,
            "image_url": primary_url,
            "preview_url": primary_url,
        },
    ), None


def materialize_image_items_traced(
    items: list[ImageItem],
    *,
    policy: AssetsPolicy,
    on_progress: ProgressCallback | None = None,
) -> tuple[list[ImageItem], list[str], PostProcessStageStat | None]:
    """批量下载图片到内存，并统计丢弃条数。"""
    if not policy.download:
        _emit_progress(on_progress, "跳过图片下载（assets.download=false）")
        return list(items), [], None

    kept: list[ImageItem] = []
    errors: list[str] = []
    before = len(items)
    _emit_progress(
        on_progress,
        f"待下载帖子 {before} 条（并行 {policy.download_workers} 线程，单张超时 {policy.timeout}s）",
    )
    for post_index, item in enumerate(items, start=1):
        platform = item.community or "unknown"
        if item.media_type.value == "video" and item.video_url:
            _emit_progress(
                on_progress,
                f"帖子 {post_index}/{before} [{platform}] {item.source_id}：视频，跳过下载",
            )
            kept.append(item)
            continue
        source_count = len(item_image_source_urls(item))
        download_count = len(_download_urls(item, policy))
        if download_count < source_count:
            _emit_progress(
                on_progress,
                f"帖子 {post_index}/{before} [{platform}] {item.source_id}："
                f"下载前 {download_count}/{source_count} 张",
            )
        else:
            _emit_progress(
                on_progress,
                f"帖子 {post_index}/{before} [{platform}] {item.source_id}："
                f"{download_count} 张图",
            )
        materialized, error = materialize_item_images(
            item,
            policy=policy,
            on_progress=on_progress,
        )
        if materialized is None:
            if error is not None:
                errors.append(error)
                _emit_progress(on_progress, f"  丢弃：{error}")
            continue
        kept.append(materialized)
        _emit_progress(on_progress, f"  帖子 {post_index}/{before} 下载完成")

    stage = PostProcessStageStat(
        stage="materialize",
        in_count=before,
        out_count=len(kept),
        dropped=before - len(kept),
    )
    return kept, errors, stage
