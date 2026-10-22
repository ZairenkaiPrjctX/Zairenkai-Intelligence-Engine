# Project context: Zairenkai-Intelligence-Engine

> Owned by this repository. Update it whenever verified facts change. Label every statement
> **Verified** (with `Evidence:`), **Unverified**, or **Unknown / Not Configured**.

## Identity

| Field | Value | Status |
|---|---|---|
| Repository | `ZairenkaiPrjctX/Zairenkai-Intelligence-Engine` | Verified. Evidence: GitHub API |
| GitHub description | AI Zairenkai | Verified. Evidence: GitHub API |
| Visibility | public | Verified. Evidence: `list_repos`, 2026-10-22 |
| Default branch | `dev` | Verified. Evidence: `git ls-remote`, 2026-10-22 |
| Purpose | Zairenkai Local AI: on-device, offline intent planning over a closed typed tool registry; Core stays the authority | Verified. Evidence: maintainer brief 2026-10-22; `zie/`, `docs/adr/0001-local-runtime-spike.md` |
| Licence | Apache-2.0 (`LICENSE`, `NOTICE`); not yet confirmed by the maintainer | **Unverified** (maintainer decision pending) |

## Contents

| Area | Location | Status |
|---|---|---|
| Phase A spike: agent loop, runtime adapter, registry, network guard | `zie/` | Verified on a Linux x86_64 host. Evidence: 14 tests, real-model test, offline proof, 2026-10-22. **Not run on Android** |
| Tool registry (5 tools) | `registry/tools.json` | Verified against the SDK schema (`ToolRegistry.load`) |
| Model manifest (Qwen2.5-0.5B-Instruct q4_0) | `models/` | Verified: SHA-256 and size match the downloaded file, 2026-10-22 |
| Evaluation | `eval/` | Verified: 9/16 on the host, 2026-10-22 |
| CI | `.github/workflows/ci.yml` | actionlint clean. **Unverified** on GitHub |

## Key facts and limitations

- Runtime for the spike: llama.cpp `b11500` (MIT), CPU. LiteRT-LM `v0.18.1` (Apache-2.0) was
  audited, not built. Verified. Evidence: ADR 0001.
- A 0.5B model routed 9 of 16 synthetic prompts correctly; not accurate enough alone. Verified.
  Evidence: `docs/SPIKE_REPORT.md`.
- No Core client: system actions stop at the preview. Verified. Evidence: `Agent.approve`, tests.

## Authoritative sources

| Topic | Source |
|---|---|
| Repository facts | this file |
| Architecture | `AGENT/ARCHITECTURE.md` |
| Organization standards | `ZairenkaiPrjctX/.github` → `agent-foundation/standards/` |
| Repository list and relationships | `ZairenkaiPrjctX/.github` → `agent-foundation/inventory/repositories.json` |

## Related repositories

- Zairenkai-Sdk: Local-AI and tool-output schemas, copied at `41481ec`. Verified. Evidence: `contracts/sources.json`.
- Zairenkai-Core: the only executor of system actions (Phase C). **Unverified**: no client yet.
- Zairenkai-App: future host of the chat UI and model manager. **Unverified**: not integrated.

## Open questions

- Which devices run the Phase B runtime comparison (one per SoC family if possible)?
- Production language: Kotlin in the app process, or a native library behind JNI?
- Which larger model (licence-cleared) is worth evaluating next?
- Confirm Apache-2.0 for this repository (maintainer).
