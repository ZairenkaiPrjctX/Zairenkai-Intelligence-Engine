#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Run eval/intents.json through the real local model and report, case by case, what it planned.

  tools/eval.py --llama <llama-completion> --model <gguf> [--out results.json]

A case passes when no forbidden tool is called and, if expect_any is not empty, at least one
expected tool is called. The numbers describe this model, this prompt and this host only.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zie import contracts  # noqa: E402
from zie.__main__ import verify_model  # noqa: E402
from zie.agent import Agent  # noqa: E402
from zie.executor import FixtureReplayExecutor  # noqa: E402
from zie.netguard import no_network  # noqa: E402
from zie.registry import ToolRegistry  # noqa: E402
from zie.runtime import LlamaCppRuntime  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, default=contracts.ROOT / "models" / "qwen2.5-0.5b-instruct-q4_0.json")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    verify_model(a.model, a.manifest)
    agent = Agent(LlamaCppRuntime(a.llama, a.model), ToolRegistry.load(), FixtureReplayExecutor())
    cases = contracts.load(contracts.ROOT / "eval" / "intents.json")["cases"]
    rows, attempts = [], []
    for c in cases:
        t0 = time.monotonic()
        with no_network(attempts):
            turn = agent.handle(c["utterance"])
        called = [i["tool_id"] for i in turn.plan["invocations"]] if turn.plan else []
        ok_forbid = not set(called) & set(c["forbid"])
        ok_expect = not c["expect_any"] or bool(set(called) & set(c["expect_any"]))
        rows.append({"utterance": c["utterance"], "called": called, "language": turn.plan["language"] if turn.plan else None,
                     "rejected": turn.rejected_reason, "pass": ok_forbid and ok_expect,
                     "seconds": round(time.monotonic() - t0, 2)})
        print(f"{'PASS' if rows[-1]['pass'] else 'FAIL'} {rows[-1]['seconds']:5.1f}s {called} ← {c['utterance']}")
    passed = sum(r["pass"] for r in rows)
    summary = {"model": a.manifest.name, "runtime": "llama.cpp", "host": f"{platform.system()} {platform.machine()}",
               "cases": len(rows), "passed": passed, "network_attempts": len(attempts),
               "language_correct": sum(r["language"] == c["language"] for r, c in zip(rows, cases)), "rows": rows}
    print(f"{passed}/{len(rows)} passed; language correct {summary['language_correct']}/{len(rows)}; network attempts {len(attempts)}")
    if a.out:
        a.out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if not attempts else 1


if __name__ == "__main__":
    sys.exit(main())
