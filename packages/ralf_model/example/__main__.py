from __future__ import annotations

import sys

from ralf_model import dump_ralf, parse_ralf

_SAMPLE = """
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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except OSError:
            pass
    doc = parse_ralf(_SAMPLE)
    print(dump_ralf(doc))


if __name__ == "__main__":
    main()
