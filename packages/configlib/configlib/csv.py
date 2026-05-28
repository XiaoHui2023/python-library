from __future__ import annotations

import csv
import os
from pathlib import Path

from .resolver import resolve_variables

SUFFIXES = {".csv"}

_KEY_VALUE_HEADERS = ("key", "value")


def is_csv(file_path: str) -> bool:
    return os.path.splitext(file_path)[1] in SUFFIXES


def load_csv(file_path: str) -> dict | list:
    data = load_csv_raw(file_path)
    return resolve_variables(data)


def load_csv_raw(file_path: str) -> dict | list:
    text = Path(file_path).read_text(encoding="utf-8-sig")
    return _parse_csv_text(text, source=file_path)


def _parse_csv_text(text: str, *, source: str) -> dict | list:
    if not text.strip():
        raise ValueError(f"CSV 文件为空: {source}")

    reader = csv.reader(text.splitlines())
    rows: list[list[str]] = []
    for row in reader:
        if not row or all(not cell.strip() for cell in row):
            continue
        rows.append([cell.strip() for cell in row])

    if not rows:
        raise ValueError(f"CSV 文件无有效内容: {source}")

    width = len(rows[0])
    if width < 2:
        raise ValueError(
            f"CSV 至少需要 2 列，实际 {width} 列: {source}"
        )

    for index, row in enumerate(rows, start=1):
        if len(row) != width:
            raise ValueError(
                f"CSV 第 {index} 行列数为 {len(row)}，"
                f"与首行 {width} 列不一致: {source}"
            )

    if width == 2:
        data_rows = rows
        if _header_matches_key_value(rows[0]):
            data_rows = rows[1:]
        return _parse_key_value_table(data_rows, source=source)

    header = rows[0]
    data_rows = rows[1:]

    if any(not name for name in header):
        raise ValueError(f"CSV 表头存在空列名: {source}")

    return _parse_record_table(header, data_rows, source=source)


def _header_matches_key_value(header: list[str]) -> bool:
    return (
        header[0].lower() == _KEY_VALUE_HEADERS[0]
        and header[1].lower() == _KEY_VALUE_HEADERS[1]
    )


def _parse_key_value_table(
    data_rows: list[list[str]],
    *,
    source: str,
) -> dict:
    result: dict[str, str] = {}
    for line_no, row in _enumerate_data_rows(data_rows, source=source, width=2):
        key, value = row
        if not key:
            raise ValueError(f"CSV 键值表第 {line_no} 行 key 为空: {source}")
        if key in result:
            raise ValueError(
                f"CSV 键值表存在重复键 {key!r}（第 {line_no} 行）: {source}"
            )
        result[key] = value
    return result


def _parse_record_table(
    header: list[str],
    data_rows: list[list[str]],
    *,
    source: str,
) -> list[dict[str, str]]:
    seen: set[str] = set()
    for name in header:
        if name in seen:
            raise ValueError(f"CSV 记录表存在重复列名 {name!r}: {source}")
        seen.add(name)

    width = len(header)
    records: list[dict[str, str]] = []
    for line_no, row in _enumerate_data_rows(data_rows, source=source, width=width):
        records.append(dict(zip(header, row, strict=True)))
    return records


def _enumerate_data_rows(
    data_rows: list[list[str]],
    *,
    source: str,
    width: int,
) -> list[tuple[int, list[str]]]:
    normalized: list[tuple[int, list[str]]] = []
    for index, row in enumerate(data_rows, start=2):
        if len(row) != width:
            raise ValueError(
                f"CSV 第 {index} 行列数为 {len(row)}，与表头 {width} 列不一致: {source}"
            )
        normalized.append((index, row))
    return normalized


__all__ = ["is_csv", "load_csv", "load_csv_raw"]
