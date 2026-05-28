from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from configlib import load_config, load_config_raw
from configlib.csv import is_csv, load_csv, load_csv_raw


class CsvHelpersTests(unittest.TestCase):
    def test_is_csv_suffix(self) -> None:
        self.assertTrue(is_csv("rules.csv"))
        self.assertFalse(is_csv("rules.tsv"))

    def test_record_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.csv"
            path.write_text(
                "name,enabled,threshold\n"
                "fast,true,10\n"
                "slow,false,30\n",
                encoding="utf-8",
            )
            data = load_csv_raw(str(path))
            self.assertEqual(
                data,
                [
                    {"name": "fast", "enabled": "true", "threshold": "10"},
                    {"name": "slow", "enabled": "false", "threshold": "30"},
                ],
            )

    def test_two_column_key_value_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pairs.csv"
            path.write_text(
                "host,127.0.0.1\n"
                "port,5432\n",
                encoding="utf-8",
            )
            data = load_csv_raw(str(path))
            self.assertEqual(data, {"host": "127.0.0.1", "port": "5432"})

    def test_key_value_table_legacy_header_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.csv"
            path.write_text(
                "Key,Value\n"
                "host,localhost\n"
                "port,8000\n",
                encoding="utf-8",
            )
            data = load_csv_raw(str(path))
            self.assertEqual(data, {"host": "localhost", "port": "8000"})

    def test_key_value_empty_data_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.csv"
            path.write_text("key,value\n", encoding="utf-8")
            self.assertEqual(load_csv_raw(str(path)), {})

    def test_record_table_empty_data_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.csv"
            path.write_text("name,enabled,threshold\n", encoding="utf-8")
            self.assertEqual(load_csv_raw(str(path)), [])

    def test_load_config_dispatches_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.csv"
            path.write_text(
                "label,${name}\n"
                "name,demo\n",
                encoding="utf-8",
            )
            self.assertEqual(load_config(path)["label"], "demo")
            self.assertEqual(load_config_raw(path)["label"], "${name}")

    def test_config_loader_accepts_key_value_csv(self) -> None:
        from configlib import ConfigLoader

        class Cfg(ConfigLoader):
            host: str = ""
            port: str = ""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.csv"
            path.write_text(
                "host,127.0.0.1\n"
                "port,8080\n",
                encoding="utf-8",
            )
            obj = Cfg.from_file(path)
            self.assertEqual(obj.host, "127.0.0.1")
            self.assertEqual(obj.port, "8080")


class CsvInvalidFormatTests(unittest.TestCase):
    def test_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "为空"):
                load_csv_raw(str(path))

    def test_single_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("only\na\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "至少需要 2 列"):
                load_csv_raw(str(path))

    def test_row_width_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "a,b\n"
                "1,2,3\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "与首行"):
                load_csv_raw(str(path))

    def test_duplicate_column_in_record_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "name,name,extra\n"
                "x,y,z\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "重复列名"):
                load_csv_raw(str(path))

    def test_duplicate_key_in_key_value_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "host,a\n"
                "host,b\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "重复键"):
                load_csv_raw(str(path))

    def test_empty_key_in_key_value_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                ",x\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "key 为空"):
                load_csv_raw(str(path))

    def test_three_column_record_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.csv"
            path.write_text(
                "key,value,extra\n"
                "a,b,c\n",
                encoding="utf-8",
            )
            data = load_csv_raw(str(path))
            self.assertEqual(
                data,
                [{"key": "a", "value": "b", "extra": "c"}],
            )

    def test_empty_header_cell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text(
                "name,,extra\n"
                "a,b,c\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "空列名"):
                load_csv_raw(str(path))

    def test_config_loader_rejects_record_table_csv(self) -> None:
        from configlib import ConfigLoader

        class Cfg(ConfigLoader):
            name: str = ""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.csv"
            path.write_text(
                "name,enabled,threshold\n"
                "a,true,10\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TypeError, "配置顶层必须是 dict"):
                Cfg.from_file(path)


if __name__ == "__main__":
    unittest.main()
