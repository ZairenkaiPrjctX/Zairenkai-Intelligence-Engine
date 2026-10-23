# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Every copy contracts/sources.json records is a file git tracks: a .gitignore pattern once hid
contracts/sdk/, so a fresh clone had no schemas and every test failed to import."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TrackedCopiesTest(unittest.TestCase):
    def test_recorded_copies_are_not_ignored(self):
        if shutil.which("git") is None or not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        copies = [f["copy"] for f in json.loads((ROOT / "contracts" / "sources.json").read_text())["files"]]
        self.assertTrue(copies)
        r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--no-index", *copies], capture_output=True, text=True)
        self.assertEqual(r.stdout, "", "ignored by .gitignore")


if __name__ == "__main__":
    unittest.main()
