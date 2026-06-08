from __future__ import annotations

from hotmeme.models import XiaohongshuPolicy
from hotmeme.sources.platform_fetch import PlatformFetchResult
from hotmeme.sources.platforms.base import PlatformWorkflow
from hotmeme.sources.platforms.xiaohongshu import XiaohongshuWorkflow
from hotmeme.sources.tikhub_client import TikHubClient

_PLATFORM_WORKFLOWS: dict[str, PlatformWorkflow] = {}


def supported_platforms() -> tuple[str, ...]:
    """返回已接入工作流的平台标识。"""
    return (XiaohongshuWorkflow.platform, *_PLATFORM_WORKFLOWS.keys())


def fetch_platform_hot_posts(
    client: TikHubClient,
    *,
    platform: str,
    xiaohongshu: XiaohongshuPolicy | None = None,
) -> PlatformFetchResult:
    """按平台标识执行对应工作流。"""
    if platform == XiaohongshuWorkflow.platform:
        workflow: PlatformWorkflow | None = XiaohongshuWorkflow(xiaohongshu)
    else:
        workflow = _PLATFORM_WORKFLOWS.get(platform)
    if workflow is None:
        return PlatformFetchResult()
    return workflow.fetch(client)
