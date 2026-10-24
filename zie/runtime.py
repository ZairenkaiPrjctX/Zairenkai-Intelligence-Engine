# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""LocalModelRuntime: the only door to a language model. Every backend runs locally.

LlamaCppRuntime runs a pinned llama.cpp `llama-completion` binary with a fixed argv (no shell),
output constrained by a JSON Schema grammar, inside an empty network namespace (`unshare -n`)
so the inference process has no network interface at all.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

MAX_OUTPUT_BYTES = 64 * 1024


class RuntimeUnavailable(RuntimeError):
    """The model cannot run here; the agent reports this instead of falling back to anything remote."""


class LocalModelRuntime(Protocol):
    name: str

    def generate(self, prompt: str, json_schema: dict[str, Any], max_tokens: int) -> str: ...


@dataclass
class LlamaCppRuntime:
    binary: Path
    model: Path
    threads: int = 4
    context: int = 2048
    timeout_s: float = 120.0
    isolate_network: bool = True
    name: str = field(default="llama.cpp", init=False)

    def argv(self, prompt: str, json_schema: dict[str, Any], max_tokens: int) -> list[str]:
        argv = [
            str(self.binary), "-m", str(self.model), "-n", str(max_tokens), "-c", str(self.context),
            "--temp", "0", "--seed", "1", "-t", str(self.threads), "-no-cnv", "--no-display-prompt",
            "--no-warmup", "--json-schema", json.dumps(json_schema, separators=(",", ":")), "-p", prompt,
        ]
        if self.isolate_network:
            unshare = shutil.which("unshare")
            if unshare is None:
                raise RuntimeUnavailable("unshare not found: refusing to run the model with network access")
            argv = [unshare, "-n", "--"] + argv
        return argv

    def generate(self, prompt: str, json_schema: dict[str, Any], max_tokens: int) -> str:
        if not self.binary.is_file() or not self.model.is_file():
            raise RuntimeUnavailable(f"model runtime not installed ({self.binary}, {self.model})")
        try:
            r = subprocess.run(self.argv(prompt, json_schema, max_tokens), capture_output=True,
                               timeout=self.timeout_s, env={"LC_ALL": "C"}, check=False)
        except subprocess.TimeoutExpired as e:
            raise RuntimeUnavailable(f"generation timed out after {self.timeout_s:.0f} s") from e
        if r.returncode != 0:
            tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["no output"]
            raise RuntimeUnavailable(f"llama.cpp exited {r.returncode}: {tail[0][:200]}")
        out = r.stdout[:MAX_OUTPUT_BYTES].decode(errors="replace")
        return out.replace("[end of text]", "").strip()


@dataclass
class ZieRunRuntime:
    """runtime/zie_run.cpp, the runner the Android app ships: llama.cpp's core libraries only,
    sampling under registry/output.gbnf (the grammar of [json_schema]; passed by file, prompt by
    file, so neither lands in a process list). Also isolated with `unshare -n` here."""

    binary: Path
    model: Path
    grammar: Path
    threads: int = 4
    context: int = 2048
    timeout_s: float = 120.0
    isolate_network: bool = True
    name: str = field(default="zie-run (llama.cpp core)", init=False)

    def generate(self, prompt: str, json_schema: dict[str, Any], max_tokens: int) -> str:
        import tempfile

        for f in (self.binary, self.model, self.grammar):
            if not f.is_file():
                raise RuntimeUnavailable(f"model runtime not installed ({f})")
        with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8") as p:
            p.write(prompt)
            p.flush()
            argv = [str(self.binary), "-m", str(self.model), "-g", str(self.grammar), "-f", p.name,
                    "-n", str(max_tokens), "-c", str(self.context), "-t", str(self.threads)]
            if self.isolate_network:
                unshare = shutil.which("unshare")
                if unshare is None:
                    raise RuntimeUnavailable("unshare not found: refusing to run the model with network access")
                argv = [unshare, "-n", "--"] + argv
            try:
                r = subprocess.run(argv, capture_output=True, timeout=self.timeout_s, env={"LC_ALL": "C"}, check=False)
            except subprocess.TimeoutExpired as e:
                raise RuntimeUnavailable(f"generation timed out after {self.timeout_s:.0f} s") from e
        if r.returncode != 0:
            tail = r.stderr.decode(errors="replace").strip().splitlines()[-1:] or ["no output"]
            raise RuntimeUnavailable(f"zie-run exited {r.returncode}: {tail[0][:200]}")
        return r.stdout[:MAX_OUTPUT_BYTES].decode(errors="replace").strip()


@dataclass
class ScriptedRuntime:
    """Test double: returns pre-written model outputs in order. Never used outside tests."""

    outputs: list[str]
    name: str = field(default="scripted (test double)", init=False)
    prompts: list[str] = field(default_factory=list, init=False)

    def generate(self, prompt: str, json_schema: dict[str, Any], max_tokens: int) -> str:
        self.prompts.append(prompt)
        if not self.outputs:
            raise RuntimeUnavailable("scripted runtime exhausted")
        return self.outputs.pop(0)
