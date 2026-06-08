from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from ralf_model import RalfParseError, dump_ralf, parse_ralf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOLDEN = FIXTURES / "syntax_golden.ralf"


def _roundtrip(src: str) -> None:
    doc = parse_ralf(src)
    doc2 = parse_ralf(dump_ralf(doc))
    assert doc.model_dump() == doc2.model_dump()


class GoldenFixtureTests(unittest.TestCase):
    def test_syntax_golden_parses(self) -> None:
        text = GOLDEN.read_text(encoding="utf-8")
        doc = parse_ralf(text)
        self.assertEqual(doc.systems[0].name, "chip")
        self.assertEqual(doc.blocks[0].name, "uart_tpl")

    def test_syntax_golden_roundtrip(self) -> None:
        _roundtrip(GOLDEN.read_text(encoding="utf-8"))


class FieldSyntaxTests(unittest.TestCase):
    def test_empty_field_body(self) -> None:
        src = """
block b {
  register r {
    bytes 1;
    field flag {}
  }
}
"""
        doc = parse_ralf(src)
        fld = doc.blocks[0].registers[0].fields[0]
        self.assertEqual(fld.name, "flag")
        self.assertEqual(fld.inner_statements, [])
        _roundtrip(src)

    def test_field_preserves_hard_reset_and_enum(self) -> None:
        src = """
block b {
  register r {
    bytes 2;
    field m @0 {
      bits 8;
      hard_reset 8'hFF;
      enum { A = 0, B = 15 };
    }
  }
}
"""
        doc = parse_ralf(src)
        inner = doc.blocks[0].registers[0].fields[0].inner_statements
        self.assertTrue(any("hard_reset" in s for s in inner))
        self.assertTrue(any("enum" in s for s in inner))
        _roundtrip(src)


class RegisterSyntaxTests(unittest.TestCase):
    def test_register_offset_decimal_and_hex(self) -> None:
        src = """
block b {
  register lo @0 {
    bytes 1;
    field f {}
  }
  register hi @'h10 {
    bytes 1;
    field g {}
  }
}
"""
        doc = parse_ralf(src)
        regs = doc.blocks[0].registers
        self.assertEqual(regs[0].offset_bytes, 0)
        self.assertEqual(regs[1].offset_bytes, 0x10)
        _roundtrip(src)

    def test_register_equals_instance_not_supported(self) -> None:
        src = """
block b {
  register flags=pci_flags;
}
"""
        with self.assertRaises(RalfParseError):
            parse_ralf(src)


class BlockSyntaxTests(unittest.TestCase):
    def test_block_forward_ref_semicolon_not_supported(self) -> None:
        src = """
block top {
  block child;
}
"""
        with self.assertRaises(RalfParseError):
            parse_ralf(src)

    def test_block_at_addr_with_body(self) -> None:
        src = """
block top {
  block bank @'h1000 {
    bytes 4;
    register r @0 {
      bytes 4;
      field x {}
    }
  }
}
"""
        doc = parse_ralf(src)
        bank = doc.blocks[0].blocks[0]
        self.assertEqual(bank.base_address, 0x1000)
        self.assertTrue(bank.has_body)
        _roundtrip(src)

    def test_block_bracket_suffix_in_hierarchical_name(self) -> None:
        src = """
block top {
  block lane = ch[3] @'h40;
}
"""
        doc = parse_ralf(src)
        sub = doc.blocks[0].blocks[0]
        self.assertEqual(sub.name, "lane")
        self.assertEqual(sub.rhs_head, "ch[3]")
        self.assertEqual(sub.base_address, 0x40)
        _roundtrip(src)


class SystemSyntaxTests(unittest.TestCase):
    def test_system_bytes_and_nested_block_ref(self) -> None:
        src = """
system soc {
  bytes 8;
  block peri @'h8000;
}
"""
        doc = parse_ralf(src)
        soc = doc.systems[0]
        self.assertEqual(soc.bytes_width, 8)
        self.assertEqual(soc.blocks[0].base_address, 0x8000)
        _roundtrip(src)

    def test_system_paren_path_at_address(self) -> None:
        src = """
system top {
  system sub (dut.cpu) @'h0;
}
"""
        doc = parse_ralf(src)
        sub = doc.systems[0].systems[0]
        self.assertEqual(sub.rhs_paren_path, "dut.cpu")
        self.assertEqual(sub.base_address, 0)
        _roundtrip(src)


class LiteralSyntaxTests(unittest.TestCase):
    def test_sized_reset_literals_in_field(self) -> None:
        src = """
block b {
  register r {
    bytes 4;
    field w @0 {
      bits 32;
      reset 32'hCAFE_0001;
    }
    field n @0 {
      bits 4;
      reset 4'b1010;
    }
  }
}
"""
        doc = parse_ralf(src)
        self.assertEqual(len(doc.blocks[0].registers[0].fields), 2)
        _roundtrip(src)


class CommentSyntaxTests(unittest.TestCase):
    def test_block_comment_around_construct(self) -> None:
        src = """
/* head */
block b /* mid */ {
  /* inner */
  bytes 1;
  register r @0 {
    bytes 1;
    field f /* tail */ {}
  }
}
"""
        doc = parse_ralf(src)
        self.assertEqual(doc.blocks[0].name, "b")
        _roundtrip(src)


@pytest.mark.parametrize(
    "snippet",
    [
        'block b { register r @\'h0 { bytes 1; field f {} } }',
        "block b { block c (a.b) @0; }",
        "system s { block b @0; }",
    ],
)
def test_minimal_snippets_roundtrip(snippet: str) -> None:
    _roundtrip(snippet)


if __name__ == "__main__":
    unittest.main()
