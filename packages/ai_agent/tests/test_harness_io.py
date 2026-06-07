from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_agent.app.harness_io import (
    classify_file_kind,
    compose_user_message_with_attachments,
    format_input_files_context,
    stage_input_files,
    StagedFile,
)


class TestHarnessIo(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_classify_file_kind(self) -> None:
        self.assertEqual(classify_file_kind(Path("a.txt")), "text")
        self.assertEqual(classify_file_kind(Path("photo.JPG")), "image")
        self.assertEqual(classify_file_kind(Path("clip.mp4")), "video")
        self.assertEqual(classify_file_kind(Path("voice.mp3")), "audio")
        self.assertEqual(classify_file_kind(Path("data.bin")), "other")

    def test_stage_input_files_and_context(self) -> None:
        source = self._root / "hello.txt"
        source.write_text("你好\n", encoding="utf-8")
        staged = stage_input_files((str(source),), self._root / "harness")
        self.assertEqual(len(staged), 1)
        self.assertEqual(staged[0].rel_path, "incoming/hello.txt")
        self.assertEqual(staged[0].kind, "text")
        self.assertTrue((self._root / "harness" / "incoming" / "hello.txt").is_file())

        context = format_input_files_context(staged)
        self.assertIn("incoming/hello.txt", context)
        self.assertIn("harness__read_file", context)
        self.assertIn("cursor_cli__run_cursor_agent", context)
        self.assertIn("output_files", context)
        self.assertIn("未在文字里提到文件名", context)

    def test_stage_duplicate_names(self) -> None:
        harness = self._root / "harness"
        first = self._root / "a.txt"
        second = self._root / "subdir"
        second.mkdir()
        copy = second / "a.txt"
        first.write_text("1", encoding="utf-8")
        copy.write_text("2", encoding="utf-8")
        staged = stage_input_files((str(first), str(copy)), harness)
        names = {item.filename for item in staged}
        self.assertEqual(names, {"a.txt", "a_2.txt"})

    def test_compose_user_message_only_attachments(self) -> None:
        staged = (
            StagedFile(
                rel_path="incoming/x.png",
                filename="x.png",
                kind="image",
                size_bytes=10,
            ),
        )
        context = format_input_files_context(staged)
        message = compose_user_message_with_attachments("", staged, context)
        self.assertIn("仅提交了附件", message)
        self.assertIn("incoming/x.png", message)
