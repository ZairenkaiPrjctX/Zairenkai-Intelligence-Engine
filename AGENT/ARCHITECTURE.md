# Architecture: Zairenkai-Intelligence-Engine

> Owned by this repository. Document only what inspected code supports, citing file paths.

## Overview

Phase A spike. One turn: utterance → `LocalModelRuntime` (llama.cpp, no network) with output
constrained to `ToolRegistry.output_schema()` → parse and re-validate → `IntentPlan`
(Zairenkai-Sdk schema) → read-only tools through a `ReadOnlyExecutor`, system tools into an
`ActionPreview` → `ExecutionResult`s and `AgentAuditEvent`s (`zie/agent.py`).

## Components

| Path | Responsibility |
|---|---|
| `zie/runtime.py` | `LocalModelRuntime`; `LlamaCppRuntime` (fixed argv, `unshare -n`, timeout, bounded output); `ScriptedRuntime` test double |
| `zie/registry.py` | closed `ToolRegistry`, argument checks, generation schema |
| `zie/agent.py` | the loop, prompt (template tokens stripped from user text), fail-closed rejections, preview, approval |
| `zie/executor.py` | `FixtureReplayExecutor`: captured outputs, labelled as replay |
| `zie/netguard.py` | blocks and records socket connects and lookups during a turn |
| `zie/contracts.py` | SDK schemas resolved offline by `$id` |
| `zie/__main__.py` | CLI; verifies the model's SHA-256 and size first |

## Trust boundaries

- Model output is untrusted: constrained, then validated against the SDK schemas and the
  registry; failure means no action.
- No root, no shell, no Core client in this repository. System actions need Core (Phase C).
- The model process has no network interface; the Python process blocks sockets.

## Generated or external artifacts

Model files and llama.cpp builds are external (never committed). `contracts/sdk/` and
`fixtures/replay/` are copies from Zairenkai-Sdk (`tools/check_sdk_copies.py`).
