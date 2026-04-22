from __future__ import annotations

import unittest

import msgpack

from patch_bay.packet_patch import apply_wire_patches


class TestPacketPatch(unittest.TestCase):
    def test_empty_steps_returns_original(self) -> None:
        b = b'{"a":1}'
        out, err = apply_wire_patches(b, [])
        self.assertIsNone(err)
        self.assertEqual(out, b)

    def test_single_patch(self) -> None:
        b = b'{"a":1,"b":2}'
        out, err = apply_wire_patches(b, [("p", {"a": 9})])
        self.assertIsNone(err)
        self.assertEqual(out, b'{"a":9,"b":2}')

    def test_sequential_patches(self) -> None:
        b = b'{"x":1,"y":2}'
        out, err = apply_wire_patches(
            b,
            [
                ("p1", {"x": 10}),
                ("p2", {"y": 20}),
            ],
        )
        self.assertIsNone(err)
        self.assertEqual(out, b'{"x":10,"y":20}')

    def test_second_patch_sees_first_mutations(self) -> None:
        b = b'{"x":1}'
        out, err = apply_wire_patches(
            b,
            [
                ("p1", {"x": 2}),
                ("p2", {"x": 3}),
            ],
        )
        self.assertIsNone(err)
        self.assertEqual(out, b'{"x":3}')

    def test_missing_key_strict(self) -> None:
        b = b'{"a":1}'
        out, err = apply_wire_patches(b, [("p", {"z": 1})])
        self.assertIsNone(out)
        self.assertIn("missing", err or "")

    def test_invalid_json(self) -> None:
        out, err = apply_wire_patches(b"not json", [("p", {"a": 1})])
        self.assertIsNone(out)
        self.assertIsNotNone(err)
        self.assertIn("msgpack", err or "")

    def test_msgpack_dict_patch(self) -> None:
        b = msgpack.packb({"a": 1, "b": 2}, use_bin_type=True)
        out, err = apply_wire_patches(b, [("p", {"a": 9})])
        self.assertIsNone(err)
        self.assertEqual(msgpack.unpackb(out or b"", raw=False), {"a": 9, "b": 2})

    def test_array_root_rejected(self) -> None:
        out, err = apply_wire_patches(b"[1,2]", [("p", {"0": 1})])
        self.assertIsNone(out)
        self.assertIn("object", err or "")

    def test_type_mismatch_int_vs_str(self) -> None:
        b = b'{"a":1}'
        out, err = apply_wire_patches(b, [("p", {"a": "x"})])
        self.assertIsNone(out)
        self.assertIn("type", err or "")

    def test_type_mismatch_int_vs_float(self) -> None:
        b = b'{"a":1}'
        out, err = apply_wire_patches(b, [("p", {"a": 1.0})])
        self.assertIsNone(out)
        self.assertIn("float", err or "")

    def test_type_match_bool(self) -> None:
        b = b'{"ok":true}'
        out, err = apply_wire_patches(b, [("p", {"ok": False})])
        self.assertIsNone(err)
        self.assertEqual(out, b'{"ok":false}')

    def test_msgpack_type_mismatch(self) -> None:
        b = msgpack.packb({"n": 42}, use_bin_type=True)
        out, err = apply_wire_patches(b, [("p", {"n": "42"})])
        self.assertIsNone(out)
        self.assertIn("str", err or "")


if __name__ == "__main__":
    unittest.main()
