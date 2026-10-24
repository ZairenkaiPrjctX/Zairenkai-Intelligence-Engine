#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Stage a model file for a GitHub release of this repository, from its ModelManifest.

The Zairenkai app downloads the model, on the user's request, from
  https://github.com/ZairenkaiPrjctX/Zairenkai-Intelligence-Engine/releases/download/<tag>/<file>
with <tag> = "model-<model_id>" and <file> = the manifest's file name, and keeps it only if its
size and SHA-256 match the manifest packaged in the app. This tool:

  urls <manifest>                              prints tag, model URL and licence URL (key=value)
  stage <manifest> <model> <licence> <out>     checks the model against the manifest and writes
                                               the release assets to <out>

The model comes from the source the manifest names, at its pinned revision; nothing is
re-encoded or renamed. Model files are never committed (CLAUDE.md).
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

REPOSITORY = "ZairenkaiPrjctX/Zairenkai-Intelligence-Engine"
SAFE_NAME = re.compile(r"[A-Za-z0-9._-]{1,128}\.gguf")
SAFE_ID = re.compile(r"[a-z0-9_]{1,64}")
HF = re.compile(r"https://huggingface\.co/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")


class ReleaseError(ValueError):
    pass


def load(manifest: Path) -> dict:
    m = json.loads(manifest.read_text())
    if m.get("schema_version") != 1 or m.get("format") != "gguf":
        raise ReleaseError("only schema 1 GGUF manifests are released")
    if len(m.get("files", [])) != 1:
        raise ReleaseError("exactly one model file per release")
    f = m["files"][0]
    if not SAFE_NAME.fullmatch(f["name"]) or not SAFE_ID.fullmatch(m["model_id"]):
        raise ReleaseError("unsafe model id or file name")
    if not re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) or not isinstance(f["size_bytes"], int) or f["size_bytes"] <= 0:
        raise ReleaseError("the manifest needs a SHA-256 and a size")
    if not HF.fullmatch(m["source"]["url"]) or not re.fullmatch(r"[0-9a-f]{40}", m["source"]["revision"]):
        raise ReleaseError("the source must be a Hugging Face repository pinned to a commit")
    return m


def tag(m: dict) -> str:
    return f"model-{m['model_id']}"


def urls(m: dict) -> dict:
    base = f"{m['source']['url']}/resolve/{m['source']['revision']}"
    return {
        "tag": tag(m),
        "model_url": f"{base}/{m['files'][0]['name']}",
        "license_url": f"{base}/LICENSE",
        "release_url": f"https://github.com/{REPOSITORY}/releases/download/{tag(m)}/{m['files'][0]['name']}",
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage(manifest: Path, model: Path, licence: Path, out: Path) -> list[Path]:
    m = load(manifest)
    f = m["files"][0]
    size = model.stat().st_size
    if size != f["size_bytes"]:
        raise ReleaseError(f"{model.name}: {size} bytes, the manifest says {f['size_bytes']}")
    digest = sha256(model)
    if digest != f["sha256"]:
        raise ReleaseError(f"{model.name}: SHA-256 {digest}, the manifest says {f['sha256']}")
    if licence.stat().st_size == 0:
        raise ReleaseError("the licence file is empty")
    out.mkdir(parents=True, exist_ok=True)
    assets = [out / f["name"], out / f"{m['model_id']}.LICENSE.txt", out / f"{m['model_id']}.manifest.json"]
    shutil.copyfile(model, assets[0])
    shutil.copyfile(licence, assets[1])
    shutil.copyfile(manifest, assets[2])
    sums = out / "SHA256SUMS"
    sums.write_text("".join(f"{digest if p == assets[0] else sha256(p)}  {p.name}\n" for p in assets))
    notes = out / "notes.md"
    u = urls(m)
    notes.write_text(
        f"{m['display_name']} for Zairenkai Local AI.\n\n"
        f"- File: `{f['name']}`, {f['size_bytes']} bytes, SHA-256 `{f['sha256']}`\n"
        f"- Source: {m['source']['url']} at revision `{m['source']['revision']}`, unchanged\n"
        f"- Licences: weights {m['licenses']['weights']}; tokenizer {m['licenses']['tokenizer']}; "
        f"configuration {m['licenses']['config']}\n\n"
        f"The Zairenkai app downloads `{u['release_url']}` only when the user asks, and keeps it only "
        "if its size and SHA-256 match the manifest packaged in the app.\n"
    )
    return assets + [sums, notes]


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 2 and argv[0] == "urls":
            for k, v in urls(load(Path(argv[1]))).items():
                print(f"{k}={v}")
            return 0
        if len(argv) == 5 and argv[0] == "stage":
            for p in stage(*map(Path, argv[1:])):
                print(p)
            return 0
    except (ReleaseError, OSError, KeyError, json.JSONDecodeError) as e:
        print(f"model_release: {e}", file=sys.stderr)
        return 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
