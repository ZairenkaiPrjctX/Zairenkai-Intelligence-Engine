# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""python -m zie --llama <llama-completion> --model <gguf> "cek kenapa HP panas"

Prints the IntentPlan, the execution results, any preview and the audit log as JSON. The model
runs in an empty network namespace and this process blocks every socket while the turn runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import contracts
from .agent import Agent
from .executor import FixtureReplayExecutor
from .netguard import no_network
from .registry import ToolRegistry
from .runtime import LlamaCppRuntime


def verify_model(model: Path, manifest: Path) -> None:
    m = contracts.load(manifest)
    errs = contracts.errors("sdk/local-ai/model-manifest.schema.json", m)
    if errs:
        raise SystemExit(f"model manifest invalid: {errs[0]}")
    entry = next((f for f in m["files"] if f["name"] == model.name), None)
    if entry is None:
        raise SystemExit(f"{model.name} is not listed in {manifest}")
    h = hashlib.sha256()
    with model.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    if h.hexdigest() != entry["sha256"] or model.stat().st_size != entry["size_bytes"]:
        raise SystemExit(f"{model} does not match the SHA-256 and size in {manifest}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="zie")
    ap.add_argument("--llama", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=contracts.ROOT / "models" / "qwen2.5-0.5b-instruct-q4_0.json")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("utterance")
    a = ap.parse_args(argv)
    verify_model(a.model, a.manifest)
    agent = Agent(LlamaCppRuntime(a.llama, a.model, threads=a.threads), ToolRegistry.load(), FixtureReplayExecutor())
    attempts: list[str] = []
    with no_network(attempts):
        turn = agent.handle(a.utterance)
    json.dump({"plan": turn.plan, "rejected": turn.rejected_reason, "results": turn.results, "preview": turn.preview,
               "audit": turn.audit, "network_attempts": attempts}, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0 if turn.plan is not None and not attempts else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
