from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import msgpack


def apply_wire_patches(
    payload: bytes,
    steps: Sequence[tuple[str, Mapping[str, Any]]],
) -> tuple[bytes | None, str | None]:
    """对根为 object 的载荷依次套用补丁；失败返回 ``(None, message)``。

    支持 **msgpack** 编码的字典（与 ``patch_jack`` 应用层一致），以及 **UTF-8 JSON** 对象（兼容旧用法）。
    每个 ``steps`` 元素为 ``(补丁名, 参数名→目标值)``。某键在**当前**对象中不存在则失败（严格存在性）；
    目标值与当前值 **Python 类型**不一致亦失败（严格类型一致）。
    """
    if not steps:
        return payload, None

    def _apply_steps(work: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
        w = dict(work)
        for patch_name, mapping in steps:
            for key, value in mapping.items():
                if key not in w:
                    return None, f"patch {patch_name!r} requires top-level key {key!r} missing"
                old = w[key]
                if type(value) is not type(old):
                    return None, (
                        f"patch {patch_name!r} key {key!r}: value type {type(value).__name__!r} "
                        f"!= original {type(old).__name__!r}"
                    )
                w[key] = value
        return w, None

    try:
        mp_obj = msgpack.unpackb(payload, raw=False, strict_map_key=False)
    except Exception:
        mp_obj = None
    if isinstance(mp_obj, dict):
        work, err = _apply_steps(mp_obj)
        if work is None:
            return None, err
        try:
            return msgpack.packb(work, use_bin_type=True), None
        except Exception as exc:
            return None, f"cannot serialize patched msgpack: {exc}"

    try:
        text = payload.decode("utf-8")
        obj = json.loads(text)
    except Exception as exc:
        return None, f"payload is not valid msgpack map or UTF-8 JSON: {exc}"
    if not isinstance(obj, dict):
        return None, "JSON root must be an object (dict)"
    work, err = _apply_steps(obj)
    if work is None:
        return None, err
    try:
        out = json.dumps(work, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except Exception as exc:
        return None, f"cannot serialize patched JSON: {exc}"
    return out, None
