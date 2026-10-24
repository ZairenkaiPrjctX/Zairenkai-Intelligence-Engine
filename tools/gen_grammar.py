#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Writes registry/output.gbnf, the grammar zie-run samples under, from registry/tools.json.

  tools/gen_grammar.py          write it
  tools/gen_grammar.py --check  fail if the committed file is not what the registry produces
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from zie import grammar  # noqa: E402
from zie.registry import ToolRegistry  # noqa: E402

OUT = ROOT / "registry" / "output.gbnf"


def main(argv):
    text = grammar.gbnf(ToolRegistry.load().output_schema())
    if argv == ["--check"]:
        if not OUT.is_file() or OUT.read_text() != text:
            print("registry/output.gbnf is out of date: run tools/gen_grammar.py", file=sys.stderr)
            return 1
        print("registry/output.gbnf is up to date")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
