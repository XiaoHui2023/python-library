from __future__ import annotations

import unittest

from patch_jack.protocol import Frame, decode_frame, encode_frame


class TestProtocol(unittest.TestCase):
    """有线帧编码与解码的往返一致性。"""

    def test_roundtrip(self) -> None:
        """编码后再解码，语义字段应保持不变。"""

        f = Frame(
            kind="send",
            payload=b"\x00\xff",
            seq=3,
        )
        raw = encode_frame(f)
        g = decode_frame(raw)
        self.assertEqual(g.kind, "send")
        self.assertEqual(g.payload, b"\x00\xff")
        self.assertEqual(g.seq, 3)


if __name__ == "__main__":
    unittest.main()
