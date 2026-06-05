from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ralf_model import RalfParseError, dump_ralf, load_ralf_file, parse_ralf
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

    def test_register_paren_path_at_offset(self) -> None:
        src = """
block top {
  bytes 4;
  register CTRL (dut.ctrl_reg) @'h0 {
    bytes 4;
    field ena(dut.ctrl_reg.en) @1 {
      bits 1;
      access rw;
    }
  }
}
"""
        doc = parse_ralf(src)
        reg = doc.blocks[0].registers[0]
        self.assertEqual(reg.name, "CTRL")
        self.assertEqual(reg.paren_path, "dut.ctrl_reg")
        self.assertEqual(reg.offset_bytes, 0)
        fld = reg.fields[0]
        self.assertEqual(fld.name, "ena")
        self.assertEqual(fld.paren_path, "dut.ctrl_reg.en")
        self.assertEqual(fld.offset_bits, 1)
        out = dump_ralf(doc)
        self.assertIn("register CTRL (dut.ctrl_reg) @'h0", out)
        self.assertIn("field ena(dut.ctrl_reg.en) @'h1", out)
        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_register_paren_path_forward_decl(self) -> None:
        src = """
block top {
  register R0 (hdl.r0) @'h10;
}
"""
        doc = parse_ralf(src)
        r = doc.blocks[0].registers[0]
        self.assertTrue(r.declaration_only)
        self.assertEqual(r.paren_path, "hdl.r0")
        self.assertEqual(r.offset_bytes, 0x10)
        out = dump_ralf(doc)
        self.assertIn("register R0 (hdl.r0) @'h10;", out)
        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

    def test_field_paren_path_no_space(self) -> None:
        src = """
block top {
  register r {
    bytes 4;
    field sig(hdl.sig) @0 {
      bits 4;
    }
  }
}
"""
        doc = parse_ralf(src)
        fld = doc.blocks[0].registers[0].fields[0]
        self.assertEqual(fld.paren_path, "hdl.sig")
        out = dump_ralf(doc)
        self.assertIn("field sig(hdl.sig)", out)
        doc2 = parse_ralf(out)
        self.assertEqual(doc.model_dump(), doc2.model_dump())

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


class ParseErrorTests(unittest.TestCase):
    def test_parse_error_includes_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.ralf"
            bad.write_text("block x {\n  ???\n}\n", encoding="utf-8")
            with self.assertRaises(RalfParseError) as ctx:
                load_ralf_file(bad, expand_source=False)
            self.assertIn(str(bad.resolve()), str(ctx.exception))

    def test_parse_error_in_included_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inc = root / "inc"
            inc.mkdir()
            (inc / "broken.ralf").write_text("block y {\n  ???\n}\n", encoding="utf-8")
            top = root / "top.ralf"
            top.write_text('source "inc/broken.ralf"\n', encoding="utf-8")
            broken = (inc / "broken.ralf").resolve()
            with self.assertRaises(RalfParseError) as ctx:
                load_ralf_file(top)
            self.assertIn(str(broken), str(ctx.exception))
            self.assertNotIn(str(top.resolve()), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
