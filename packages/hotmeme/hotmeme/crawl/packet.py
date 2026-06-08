from __future__ import annotations



from datetime import datetime



from pydantic import BaseModel, ConfigDict, Field



from hotmeme.models import FetchDiagnostics, ImageItem, TikHubApiCall





class HotMemeCrawlPacket(BaseModel):

    """单次爬取数据包。"""



    model_config = ConfigDict(extra="forbid")



    crawled_at: datetime = Field(description="爬取完成时间")

    new_items: list[ImageItem] = Field(

        default_factory=list,

        description="相对上次爬取新增的热帖项",

    )

    fetched_items: list[ImageItem] = Field(

        default_factory=list,

        description="本轮拉取到的全部热帖项（含已见过）",

    )

    providers_ok: list[str] = Field(default_factory=list, description="成功的来源")

    providers_failed: list[str] = Field(default_factory=list, description="失败的来源")

    fetch_errors: list[str] = Field(

        default_factory=list,

        description="拉取过程中的错误说明",

    )

    api_calls: list[TikHubApiCall] = Field(

        default_factory=list,

        description="本轮 TikHub HTTP 请求（按次计费）",

    )

    is_initial: bool = Field(

        default=False,

        description="是否为实例创建后的首次爬取",

    )

    diagnostics: FetchDiagnostics | None = Field(

        default=None,

        description="解析与过滤阶段统计（调试）",

    )

