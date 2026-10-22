#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Check the files copied from Zairenkai-Sdk (contracts/sources.json).

  tools/check_sdk_copies.py               every copy matches its recorded SHA-256
  tools/check_sdk_copies.py <sdk checkout> and equals the SDK file at the pinned commit
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str]) -> int:
    src = json.loads((ROOT / "contracts/sources.json").read_text(encoding="utf-8"))
    commit, bad = src["sdk"]["commit"], 0
    for f in src["files"]:
        data = (ROOT / f["copy"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != f["sha256"]:
            print(f"FAIL {f['copy']}: SHA-256 differs from contracts/sources.json")
            bad += 1
            continue
        if argv:
            r = subprocess.run(["git", "-C", argv[0], "show", f"{commit}:{f['sdk_path']}"], capture_output=True, timeout=60)
            if r.returncode != 0 or r.stdout != data:
                print(f"FAIL {f['copy']}: differs from Zairenkai-Sdk {commit[:12]}:{f['sdk_path']}")
                bad += 1
                continue
        print(f"ok   {f['copy']}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
