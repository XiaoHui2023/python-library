from __future__ import annotations

import unittest

from ralf_model import dump_ralf, parse_ralf
from ralf_model.parse import normalize_ralf_whitespace


class RalfRoundtripTests(unittest.TestCase):
    def test_ug_snippet_roundtrip_semantics(self) -> None:
        src = """
block b1 {
  bytes 1;
  register r {
    bytes 1;
    field WDT_EN @'h5 {
      bits 1;
      reset 'h0;
      access rw;
      enum { ENABLE = 1, DISABLE = 0 };
    }
  }
}
"""
        doc = parse_ralf(src)
        self.assertEqual(doc.blocks[0].name, "b1")
        self.assertEqual(doc.blocks[0].bytes_width, 1)
        reg = doc.blocks[0].registers[0]
        self.assertEqual(reg.name, "r")
        self.assertFalse(reg.declaration_only)
        fld = reg.fields[0]
        self.assertEqual(fld.name, "WDT_EN")
        self.assertEqual(fld.offset_bits, 5)
        self.assertIn("enum { ENABLE = 1, DISABLE = 0 };", fld.inner_statements)

        out = dump_ralf(doc)
        self.assertIn("field WDT_EN @'h5", out)
        self.assertIn("bits 1;", out)
        self.assertIn("reset 'h0;", out)
        self.assertIn("access rw;", out)

        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_block_instance_rename_equals_rhs(self) -> None:
        """用户指南示例：在父 block 内 ``block inst = blk1;`` 实例化并改名。"""
        src = """
block top {
  block inst = blk1;
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "inst")
        self.assertEqual(sub.rhs_head, "blk1")
        self.assertFalse(sub.has_body)
        out = dump_ralf(doc)
        self.assertIn("block inst = blk1;", out)
        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_block_ref_with_body(self) -> None:
        src = """
block top {
  block u = sub {
    bytes 4;
  }
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.rhs_head, "sub")
        self.assertTrue(sub.has_body)
        self.assertEqual(sub.bytes_width, 4)
        doc2 = parse_ralf(dump_ralf(doc))
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_block_hierarchical_name_and_brackets(self) -> None:
        src = """
block top {
  block blk_vh = blk_vh[2];
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "blk_vh")
        self.assertEqual(sub.rhs_head, "blk_vh[2]")
        out = dump_ralf(doc)
        self.assertIn("block blk_vh = blk_vh[2];", out)

    def test_block_dotted_instance_name(self) -> None:
        src = """
block top {
  block bridge.apb = br;
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "bridge.apb")
        self.assertEqual(sub.rhs_head, "br")

    def test_block_simple_at_address(self) -> None:
        src = """
block top {
  block myblk @'h1000;
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "myblk")
        self.assertEqual(sub.base_address, 0x1000)
        self.assertIsNone(sub.rhs_head)
        self.assertFalse(sub.has_body)
        self.assertIn("block myblk @'h1000;", dump_ralf(doc))
        doc2 = parse_ralf(dump_ralf(doc))
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_block_equals_instance_path_at_address(self) -> None:
        src = """
block top {
  block uart_blk = uart_inst (dut.uart0) @'h2000;
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "uart_blk")
        self.assertEqual(sub.rhs_head, "uart_inst")
        self.assertEqual(sub.rhs_paren_path, "dut.uart0")
        self.assertEqual(sub.base_address, 0x2000)
        self.assertFalse(sub.has_body)
        out = dump_ralf(doc)
        self.assertIn("block uart_blk = uart_inst (dut.uart0) @'h2000;", out)
        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_register_forward_decl(self) -> None:
        src = """
block top {
  register R0;
}
"""
        doc = parse_ralf(src)
        r = doc.blocks[0].registers[0]
        self.assertTrue(r.declaration_only)
        self.assertEqual(r.name, "R0")
        out = dump_ralf(doc)
        self.assertIn("register R0;", out)

    def test_block_ref_rhs_with_parentheses(self) -> None:
        src = """
block top {
  block bridge.apb = br (amba_bus.bridge);
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.rhs_head, "br")
        self.assertEqual(sub.rhs_paren_path, "amba_bus.bridge")
        self.assertFalse(sub.has_body)

    def test_nested_block(self) -> None:
        src = """
block a {
  block b {
    bytes 2;
  }
}
"""
        doc = parse_ralf(src)
        self.assertEqual(doc.blocks[0].blocks[0].name, "b")
        self.assertEqual(doc.blocks[0].blocks[0].bytes_width, 2)

    def test_normalize_whitespace(self) -> None:
        src = "block  x  {  // c\n bytes 1 ; } "
        n = normalize_ralf_whitespace(src)
        self.assertNotIn("//", n)


if __name__ == "__main__":
    unittest.main()
