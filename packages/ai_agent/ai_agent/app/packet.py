from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RunInputPacket(BaseModel):
    """
    应用运行入口的输入数据包。

    由调用方构造并传入 ``AgentApp.run``；会话状态落在磁盘，单次调用结束后不保留会话实例。
    """

    model_config = ConfigDict(extra="forbid")

    user_name: str = Field(description="用户显示名，写入对话与记忆讲述者字段")
    session_id: str = Field(description="会话标识，对应沙箱下 sessions/<id>/ 目录")
    request: str = Field(description="本轮用户要求或任务说明")
    input_files: tuple[str, ...] = Field(
        default_factory=tuple,
        description="用户传入的本地文件绝对或相对路径，将复制到本会话 Harness 的 incoming/ 下",
    )
    clear: bool = Field(
        default=False,
        description="为 True 时清空本会话 Harness 工作区、分层记忆存储与无 Memory 时的对话持久化",
    )


class RunOutputPacket(BaseModel):
    """应用运行入口的输出数据包。"""

    model_config = ConfigDict(extra="forbid")

    user_name: str = Field(description="与输入包一致的用户名")
    session_id: str = Field(description="与输入包一致的会话 id")
    answer: str = Field(description="助手面向用户的最终文本")
    output_files: tuple[str, ...] = Field(
        default_factory=tuple,
        description="模型声明须返回的文件路径（已解析为宿主机绝对路径且文件存在）",
    )
