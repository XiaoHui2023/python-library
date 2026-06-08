from __future__ import annotations

from pathlib import Path

from hotmeme.crawl.packet import HotMemeCrawlPacket
from hotmeme.hotmeme import HotMeme


def crawl_once(
    *,
    client: HotMeme | None = None,
    config_path: Path | str | None = None,
    tikhub_enabled: bool = True,
    api_key: str | None = None,
    base_url: str = "https://api.tikhub.io",
    source_timeout: float = 5.0,
    allow_nsfw: bool = False,
    platforms: list[str] | None = None,
    per_source_timeout: float = 5.0,
    retries: int = 1,
    skip_failed_providers: bool = True,
) -> HotMemeCrawlPacket:
    """执行一次热帖爬取。

    传入 ``client`` 时复用其增量记忆；否则按平铺参数临时构造 ``HotMeme``。

    Args:
        client: 已有聚合器实例。
        config_path: YAML/JSON 配置文件；指定时忽略其余构造项。
        tikhub_enabled: 是否启用 TikHub。
        api_key: TikHub API key。
        base_url: TikHub API 根地址。
        source_timeout: TikHub 请求超时秒数。
        allow_nsfw: 是否允许 NSFW 内容。
        platforms: 拉帖平台列表。
        per_source_timeout: 单平台聚合超时秒数。
        retries: 失败重试次数。
        skip_failed_providers: 单平台失败时是否跳过并继续。

    Returns:
        本次爬取增量数据包。
    """
    if client is None:
        client = HotMeme(
            config_path=config_path,
            tikhub_enabled=tikhub_enabled,
            api_key=api_key,
            base_url=base_url,
            source_timeout=source_timeout,
            allow_nsfw=allow_nsfw,
            platforms=platforms,
            per_source_timeout=per_source_timeout,
            retries=retries,
            skip_failed_providers=skip_failed_providers,
        )
    return client.crawl_once()
