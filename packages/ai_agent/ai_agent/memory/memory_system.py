from __future__ import annotations



import threading

from datetime import datetime, timezone

from pathlib import Path

from typing import Literal



from openai import AsyncOpenAI



from ai_agent.context import ChatMessage

from ai_agent.llm_openai import OpenAILLM

from ai_agent.memory.compressor import (

    LLMMemoryCompressor,

    MemoryCompressor,

    RuleMemoryCompressor,

)

from ai_agent.memory.config import MemoryConfig

from ai_agent.memory.compression_work import CompressionResult, CompressionWork

from ai_agent.memory.context_builder import BuiltMemoryContext, build_memory_context

from ai_agent.memory.models import ImportantMemoryEntry, MemoryMessage, MemorySnapshot

from ai_agent.memory.snapshot_merge import apply_result, prepare_work

from ai_agent.memory.store import MemoryStore

from ai_agent.memory.worker import (

    MemoryTask,

    MemoryTaskKind,

    MemoryWorker,

    expire_old_date_days,

)



MessageRole = Literal["user", "assistant"]





class MemorySystem:

    """

    单会话分层记忆入口：短期、日期、长期与重要记忆。



    Agent 每轮读取已发布视图；压缩在独立线程中执行，完成后发布新视图，不阻塞主推理。

    """



    def __init__(

        self,

        storage_dir: Path | str,

        *,

        api_key: str,

        model: str,

        base_url: str,

        config: MemoryConfig | None = None,

        autostart: bool = True,

        use_llm_compressor: bool = True,

        compressor: MemoryCompressor | None = None,

    ) -> None:

        if not api_key.strip():

            raise ValueError("api_key 不能为空")

        if not model.strip():

            raise ValueError("model 不能为空")

        if not base_url.strip():

            raise ValueError("base_url 不能为空")



        self._storage_dir = Path(storage_dir)

        self._config = config or MemoryConfig()

        self._api_key = api_key.strip()

        self._model = model.strip()

        self._base_url = base_url.strip().rstrip("/")

        self._use_llm = use_llm_compressor

        self._inject_compressor = compressor

        self._store = MemoryStore(self._storage_dir)

        self._lock = threading.RLock()

        self._live = self._store.load()

        self._agent_view = self._live.model_copy(deep=True)

        self._worker = MemoryWorker(

            config=self._config,

            compressor_factory=self._make_compressor,

            prepare=self._worker_prepare,

            commit=self._worker_commit,

        )

        if autostart:

            self._worker.start()

        self._schedule_expired_dates()



    @property

    def storage_dir(self) -> Path:

        """本会话记忆存储目录。"""

        return self._storage_dir



    @property

    def config(self) -> MemoryConfig:

        return self._config



    def append(

        self,

        *,

        speaker: str,

        role: MessageRole,

        content: str,

        at: datetime | None = None,

    ) -> None:

        """

        追加一条对话到短期记忆，并在超出上限时触发压缩任务。



        Args:

            speaker: 讲述者显示名（多用户场景区分身份）

            role: user 或 assistant

            content: 原文

            at: 发生时刻，默认 UTC 当前时间

        """

        label = speaker.strip()

        if not label:

            raise ValueError("speaker 不能为空")

        text = content.strip()

        if not text:

            return

        stamp = at or datetime.now(timezone.utc)

        if stamp.tzinfo is None:

            stamp = stamp.replace(tzinfo=timezone.utc)

        msg = MemoryMessage(speaker=label, role=role, content=text, at=stamp)

        with self._lock:

            self._live.short_term.append(msg)

            self._sync_agent_short_term()

            self._store.save_short_term(self._live.short_term)

            self._maybe_overflow_short_term()



    def remember(self, content: str, *, source: str = "explicit") -> None:

        """

        直接写入重要记忆。



        Args:

            content: 要记住的文本

            source: 来源标记

        """

        text = content.strip()

        if not text:

            return

        now = datetime.now(timezone.utc)

        with self._lock:

            self._live.important.append(

                ImportantMemoryEntry(at=now, content=text, source=source),

            )

            self._sync_agent_important()

            self._store.save_important(self._live.important)

            self._maybe_compress_important()



    def build_context(self) -> BuiltMemoryContext:

        """生成供 Agent.run 使用的系统补充与消息列表（读已发布视图，不等待压缩）。"""

        view = self._copy_agent_view()

        return build_memory_context(view)



    def context_for_agent(

        self,

        *,

        system_prompt: str,

    ) -> tuple[str, list[ChatMessage]]:

        """

        合并系统提示与记忆，返回 (完整 system_prompt, messages)。



        Args:

            system_prompt: 调用方原始系统提示



        Returns:

            拼接记忆后的系统提示与短期消息列表

        """

        ctx = self.build_context()

        if ctx.system_supplement:

            merged = system_prompt.rstrip() + "\n\n" + ctx.system_supplement

        else:

            merged = system_prompt

        return merged, list(ctx.messages)



    def flush(self, *, timeout: float = 30.0) -> None:

        """等待后台队列中已有压缩任务完成。"""

        self._worker.drain(timeout=timeout)



    def shutdown(self, *, join: bool = True, timeout: float = 5.0) -> None:

        """停止后台线程。"""

        self._worker.stop(join=join, timeout=timeout)



    def _copy_agent_view(self) -> MemorySnapshot:

        with self._lock:

            return self._agent_view.model_copy(deep=True)



    def _publish_agent_view(self) -> None:

        self._agent_view = self._live.model_copy(deep=True)



    def _sync_agent_short_term(self) -> None:

        self._agent_view.short_term = [

            m.model_copy(deep=True) for m in self._live.short_term

        ]



    def _sync_agent_important(self) -> None:

        self._agent_view.important = [

            e.model_copy(deep=True) for e in self._live.important

        ]



    def _worker_prepare(self, task: MemoryTask) -> CompressionWork | None:

        with self._lock:

            return prepare_work(self._live, task, config=self._config)



    def _worker_commit(

        self,

        task: MemoryTask,

        work: CompressionWork,

        result: CompressionResult,

    ) -> None:

        followups: list[MemoryTask] = []

        with self._lock:

            followups = apply_result(

                self._live,

                task,

                work,

                result,

                config=self._config,

            )

            self._publish_agent_view()

            self._persist_all_layers()

            if task.kind == MemoryTaskKind.SHORT_TO_DATE:

                self._maybe_overflow_short_term()

            if task.kind == MemoryTaskKind.COMPRESS_IMPORTANT:

                self._maybe_compress_important()

            if task.kind == MemoryTaskKind.COMPRESS_LONG:

                if len(self._live.long_term) > self._config.long_term_max_chunks:

                    followups.append(MemoryTask(MemoryTaskKind.COMPRESS_LONG, {}))

        for follow in followups:

            self._worker.enqueue(follow)



    def _make_compressor(self) -> MemoryCompressor:

        if self._inject_compressor is not None:

            return self._inject_compressor

        if not self._use_llm:

            return RuleMemoryCompressor()

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

        llm = OpenAILLM(client, model=self._model)

        return LLMMemoryCompressor(llm)



    def _persist_all_layers(self) -> None:

        self._store.save_short_term(self._live.short_term)

        active_dates = {day.date for day in self._live.date_days}

        for day in self._live.date_days:

            self._store.save_date_day(day)

        self._store.prune_date_files(active_dates)

        self._store.save_long_term(self._live.long_term)

        self._store.save_important(self._live.important)



    def _maybe_overflow_short_term(self) -> None:

        limit = self._config.short_term_max_messages

        if len(self._live.short_term) <= limit:

            return

        batch = min(

            self._config.short_term_overflow_batch,

            len(self._live.short_term),

        )

        self._worker.enqueue(

            MemoryTask(

                MemoryTaskKind.SHORT_TO_DATE,

                {"batch_size": batch},

            ),

        )



    def _maybe_compress_important(self) -> None:

        if len(self._live.important) <= self._config.important_max_entries:

            return

        self._worker.enqueue(

            MemoryTask(MemoryTaskKind.COMPRESS_IMPORTANT, {}),

        )



    def _schedule_expired_dates(self) -> None:

        with self._lock:

            expired = expire_old_date_days(

                self._live,

                config=self._config,

            )

            for day_label in expired:

                self._worker.enqueue(

                    MemoryTask(

                        MemoryTaskKind.DATE_TO_LONG,

                        {"day": day_label},

                    ),

                )

            if len(self._live.long_term) > self._config.long_term_max_chunks:

                self._worker.enqueue(

                    MemoryTask(MemoryTaskKind.COMPRESS_LONG, {}),

                )


