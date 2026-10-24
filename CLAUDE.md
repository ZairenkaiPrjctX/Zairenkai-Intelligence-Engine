# CLAUDE.md: Zairenkai-Intelligence-Engine

Instructions for Claude Code in `ZairenkaiPrjctX/Zairenkai-Intelligence-Engine`. Keep this file under 200 lines;
put detail in `AGENT/`.

@AGENTS.md
@AGENT/PROJECT_CONTEXT.md

## Current state (read first)

This repository holds the **Zairenkai Local AI Phase A spike** (Python ≥ 3.11): a local model
(llama.cpp, offline) maps a request to a typed `IntentPlan` against a closed `ToolRegistry`.
Decision: `docs/adr/0001-local-runtime-spike.md`. Results: `docs/SPIKE_REPORT.md`. It is a
feasibility harness, not the on-device product.

Non-negotiables in this repo:
- **No remote AI API, ever.** Inference runs locally; the model process runs with no network
  (`unshare -n`) and the agent blocks sockets during a turn. Model download is separate and
  user-initiated; never upload prompts, telemetry or device identifiers.
- **Structured tool calling only.** The registry is closed and typed; the model cannot add tools,
  emit code, shell, paths or URLs. Invalid output yields no action.
- **No privilege here.** System tools only produce an `ActionPreview`; execution belongs to
  Zairenkai-Core after explicit approval. Never report an action applied without Core's verified
  result.
- Contracts come from Zairenkai-Sdk (`contracts/sdk/`, pinned); never edit the copies.
- Never commit model files or runtime builds. Every model needs a `ModelManifest` with SHA-256 and
  separate licences for weights, tokenizer and configuration. Models reach the app only through a
  release `model-<model_id>` that the **Model release** workflow drafts from the manifest's pinned
  source and a maintainer publishes (`docs/MODEL_RELEASE.md`); never replace a published model.
- Test doubles (`ScriptedRuntime`, fixture replay) are labelled; never present them as a real
  model or a device.

## Commands

| Purpose | Command | Status |
|---|---|---|
| Set up | `python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock` | Verified. Evidence: 2026-10-22 |
| Test | `.venv/bin/python -m unittest discover -s tests -t . -v` | Verified. Evidence: 19 passed, 1 skipped (real model not configured), 2026-10-24 |
| Real-model test | `ZIE_LLAMA=<llama-completion> ZIE_MODEL=<gguf> .venv/bin/python -m unittest tests.test_real_model` | Verified. Evidence: passed, llama.cpp b11500, Qwen2.5-0.5B q4_0, Linux x86_64, 2026-10-22 |
| Offline proof | `PYTHON=.venv/bin/python tools/offline-proof.sh <llama-completion> <gguf>` | Verified. Evidence: exit 0, no interface but lo, 0 network attempts, 2026-10-22 |
| Evaluation | `.venv/bin/python tools/eval.py --llama <bin> --model <gguf>` | Verified. Evidence: 9/16 passed (`eval/results-2026-10-22-…json`) |
| SDK copies | `.venv/bin/python tools/check_sdk_copies.py <Zairenkai-Sdk checkout>` | Verified. Evidence: all ok at SDK `41481ec`, 2026-10-22 |
| Shell / workflow lint | `shellcheck tools/*.sh`; `actionlint .github/workflows/*.yml` | Verified. Evidence: clean, 2026-10-24 |
| Model release (maintainer) | GitHub Actions **Model release** on `dev`, `draft_release` (`docs/MODEL_RELEASE.md`); locally `python3 tools/model_release.py urls\|stage …` | Verified locally. Evidence: `stage` accepted the real Qwen2.5-0.5B q4_0 file (SHA-256 `7671c0c3…`), 2026-10-24; the workflow has never run |
| Validate agent foundation | `python3 <path-to-.github>/agent-foundation/scripts/validate_agent_setup.py .` | Configured |

Only list commands that exist in this repository. Never invent one.

## Working rules

- Inspect the relevant code before editing it. Preserve unrelated and uncommitted changes.
- Generated files are edited at their source, then regenerated. Managed foundation files
  (listed in `AGENT/.foundation-manifest.json`) are edited in `ZairenkaiPrjctX/.github`, not here.
- Destructive or outward-facing actions (deleting data, force-push, history rewrites,
  publishing releases, deploying, flashing devices) need explicit human approval each time.
- Do not claim a build, test, or signature succeeded without showing the output.

## Git

- Work on a topic branch; open **draft** pull requests; never merge or approve.
- Commits must be cryptographically signed. If signing fails, stop and report the error.
  Trailer format and verification: `AGENT/policies/git-and-commit-signing.md`.

## Where things are

- `AGENT/README.md`: index of the agent library (prompts, policies, playbooks, templates).
- `.claude/skills/`: run `/repo-audit`, `/implement-feature`, `/bug-fix`, `/test-and-verify`,
  `/security-review`, `/release-readiness`.
- `.claude/rules/`: path-scoped rules, loaded automatically.
