from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_agent import AgentApp, AgentListener, RunInputPacket
import ai_agent.app.app as app_module
from ai_agent.app.output_format import parse_structured_run_output
from ai_agent.app.session_store import load_conversation, save_conversation
from ai_agent.context import ChatMessage
from ai_agent.llm import StreamChunk, StreamKind
from script_llm import ScriptLLM


class TestParseStructuredOutput(unittest.TestCase):
    def test_plain_json(self) -> None:
        payload = {"answer": "你好", "output_files": ["out/a.txt"]}
        answer, files = parse_structured_run_output(json.dumps(payload))
        self.assertEqual(answer, "你好")
        self.assertEqual(files, ("out/a.txt",))

    def test_fallback_raw_text(self) -> None:
        answer, files = parse_structured_run_output("纯文本回答")
        self.assertEqual(answer, "纯文本回答")
        self.assertEqual(files, ())

    def test_markdown_fence_and_trailing_prose(self) -> None:
        inner = json.dumps(
            {"answer": "好的，Alice！", "output_files": []},
            ensure_ascii=False,
        )
        raw = f"确认完毕。\n\n```json\n{inner}\n```\n\n如有问题请继续提问。"
        answer, files = parse_structured_run_output(raw)
        self.assertEqual(answer, "好的，Alice！")
        self.assertEqual(files, ())


class TestSessionStore(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            messages = [
                ChatMessage(role="user", content="hi", name="alice"),
                ChatMessage(role="assistant", content="hello"),
            ]
            save_conversation(root, messages)
            loaded = load_conversation(root)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].name, "alice")


def _patch_build_session_with_llm(llm: ScriptLLM):
    real_build = app_module.build_session

    def wrapped(**kwargs):
        session = real_build(**kwargs)
        session.agent.context.llm = llm
        return session

    return patch.object(app_module, "build_session", side_effect=wrapped)


class TestAgentAppRun(unittest.IsolatedAsyncioTestCase):
    async def test_run_packet_ephemeral_session(self) -> None:
        final_json = json.dumps(
            {"answer": "完成", "output_files": []},
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta=final_json)],
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            rule_file = Path(tmp) / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
            )
            packet = RunInputPacket(
                user_name="测试用户",
                session_id="run-once",
                request="请处理",
                clear=True,
            )
            with _patch_build_session_with_llm(llm):
                out = await app.run(packet)
            self.assertFalse(app.has_session("run-once"))
            self.assertEqual(out.answer, "完成")
            self.assertEqual(out.user_name, "测试用户")

    async def test_run_notifies_app_run_end(self) -> None:
        final_json = json.dumps(
            {"answer": "终稿", "output_files": []},
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta=final_json)],
            ],
        )
        seen: list[str] = []
        listener = AgentListener(
            on_app_run_end=lambda packet: seen.append(packet.answer),
        )
        with tempfile.TemporaryDirectory() as tmp:
            rule_file = Path(tmp) / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                listeners=listener,
            )
            packet = RunInputPacket(
                user_name="u",
                session_id="notify",
                request="请处理",
                clear=True,
            )
            with _patch_build_session_with_llm(llm):
                out = await app.run(packet)
            self.assertEqual(out.answer, "终稿")
            self.assertEqual(seen, ["终稿"])

    async def test_run_restores_conversation_without_clear(self) -> None:
        final_json = json.dumps(
            {"answer": "第二次", "output_files": []},
            ensure_ascii=False,
        )
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta=final_json)],
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            rule_file = Path(tmp) / "rules.md"
            rule_file.write_text("规则", encoding="utf-8")
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
            )
            session_root = app.sandbox_root / "sessions" / "persist"
            session_root.mkdir(parents=True)
            save_conversation(
                session_root,
                [ChatMessage(role="user", content="旧消息")],
            )
            packet = RunInputPacket(
                user_name="u",
                session_id="persist",
                request="继续",
                clear=False,
            )
            with _patch_build_session_with_llm(llm):
                out = await app.run(packet)
            self.assertEqual(out.answer, "第二次")
            history = load_conversation(session_root)
            self.assertGreaterEqual(len(history), 2)

    async def test_run_plain_text_answer(self) -> None:
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta="直接回答")],
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            rule_file = Path(tmp) / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            app = AgentApp(
                tmp,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
            )
            packet = RunInputPacket(
                user_name="测试用户",
                session_id="direct",
                request="你好",
                clear=True,
            )
            with _patch_build_session_with_llm(llm):
                out = await app.run(packet)
            self.assertEqual(out.answer, "直接回答")

    async def test_run_discards_input_files_when_harness_disabled(self) -> None:
        llm = ScriptLLM(
            _scripts=[
                [StreamChunk(kind=StreamKind.TEXT, delta="只处理文本")],
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rule_file = root / "rules.md"
            rule_file.write_text("你是助手", encoding="utf-8")
            input_file = root / "photo.png"
            input_file.write_bytes(b"fake image")
            app = AgentApp(
                root,
                rule_paths=[rule_file],
                api_key="k",
                model="m",
                base_url="https://example.invalid/v1",
                harness_enabled=False,
            )
            packet = RunInputPacket(
                user_name="测试用户",
                session_id="discard-files",
                request="看一下",
                input_files=(str(input_file),),
                clear=True,
            )
            with _patch_build_session_with_llm(llm):
                out = await app.run(packet)
            self.assertEqual(out.answer, "只处理文本")
            incoming = root / "sessions" / "discard-files" / "harness" / "incoming"
            self.assertFalse(incoming.exists())
