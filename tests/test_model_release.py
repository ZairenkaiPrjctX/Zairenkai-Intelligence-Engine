# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""tools/model_release.py: the release tag and URLs the app derives, and the checks before a
model file becomes a release asset. Stand-in files only; the real model is never needed here."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import model_release as mr  # noqa: E402

MANIFEST = ROOT / "models" / "qwen2.5-0.5b-instruct-q4_0.json"


class ModelReleaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.data = b"GGUF stand-in"
        m = json.loads(MANIFEST.read_text())
        m["files"][0]["sha256"] = hashlib.sha256(self.data).hexdigest()
        m["files"][0]["size_bytes"] = len(self.data)
        self.manifest = self.dir / "m.json"
        self.manifest.write_text(json.dumps(m))
        self.model = self.dir / "model.gguf"
        self.model.write_bytes(self.data)
        self.licence = self.dir / "LICENSE"
        self.licence.write_text("Apache License 2.0\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_real_manifest_gives_the_urls_the_app_derives(self):
        u = mr.urls(mr.load(MANIFEST))
        self.assertEqual(u["tag"], "model-qwen2_5_0_5b_instruct_q4_0")
        self.assertEqual(
            u["release_url"],
            "https://github.com/ZairenkaiPrjctX/Zairenkai-Intelligence-Engine/releases/download/"
            "model-qwen2_5_0_5b_instruct_q4_0/qwen2.5-0.5b-instruct-q4_0.gguf",
        )
        self.assertEqual(
            u["model_url"],
            "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/"
            "9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_0.gguf",
        )

    def test_a_matching_file_is_staged_with_its_licence_manifest_and_sums(self):
        out = self.dir / "out"
        assets = mr.stage(self.manifest, self.model, self.licence, out)
        names = sorted(p.name for p in assets)
        self.assertEqual(names, sorted([
            "qwen2.5-0.5b-instruct-q4_0.gguf", "qwen2_5_0_5b_instruct_q4_0.LICENSE.txt",
            "qwen2_5_0_5b_instruct_q4_0.manifest.json", "SHA256SUMS", "notes.md",
        ]))
        self.assertEqual((out / "qwen2.5-0.5b-instruct-q4_0.gguf").read_bytes(), self.data)
        sums = dict(reversed(l.split("  ")) for l in (out / "SHA256SUMS").read_text().splitlines())
        self.assertEqual(sums["qwen2.5-0.5b-instruct-q4_0.gguf"], hashlib.sha256(self.data).hexdigest())
        self.assertIn("only when the user asks", (out / "notes.md").read_text())

    def test_a_file_that_does_not_match_is_refused(self):
        self.model.write_bytes(self.data + b"x")
        with self.assertRaises(mr.ReleaseError):
            mr.stage(self.manifest, self.model, self.licence, self.dir / "out")
        self.model.write_bytes(b"X" + self.data[1:])
        with self.assertRaisesRegex(mr.ReleaseError, "SHA-256"):
            mr.stage(self.manifest, self.model, self.licence, self.dir / "out")
        self.assertFalse((self.dir / "out" / "SHA256SUMS").exists())

    def test_unpinned_or_unsafe_manifests_are_refused(self):
        m = json.loads(self.manifest.read_text())
        for change in (
            lambda d: d["source"].update(revision="main"),
            lambda d: d["source"].update(url="https://example.com/x/y"),
            lambda d: d["files"][0].update(name="../x.gguf"),
            lambda d: d.update(model_id="Bad Id"),
        ):
            d = json.loads(json.dumps(m))
            change(d)
            self.manifest.write_text(json.dumps(d))
            with self.assertRaises(mr.ReleaseError):
                mr.load(self.manifest)


if __name__ == "__main__":
    unittest.main()
