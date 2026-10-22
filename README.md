# Zairenkai-Intelligence-Engine

Zairenkai Local AI: an on-device assistant that turns a typed request into calls of a closed,
typed tool registry. **Phase A spike** (feasibility), not the product.

- Inference is local and offline: no remote AI API. The model process runs in an empty network
  namespace, and the agent blocks every socket while a turn runs.
- The model emits an `IntentPlan` (Zairenkai-Sdk schema), constrained at generation time to the
  registry's schema and validated again after; anything else is rejected with no action.
- Read-only tools run; system tools (for example `fas.set_profile`) only produce an
  `ActionPreview`. Execution belongs to Zairenkai-Core after explicit approval (Phase C).

| Path | Content |
|---|---|
| `zie/` | agent loop, `LocalModelRuntime` (llama.cpp), closed `ToolRegistry`, network guard, fixture-replay executor |
| `registry/tools.json` | the five tools of the spike |
| `models/` | `ModelManifest` of the evaluated model (the model file is not in Git) |
| `contracts/sdk/`, `fixtures/replay/` | copies from Zairenkai-Sdk at a pinned commit (`contracts/sources.json`) |
| `eval/` | 16 synthetic bilingual prompts and the recorded results |
| `docs/adr/0001-local-runtime-spike.md` | llama.cpp vs LiteRT-LM, with commits and licences |
| `docs/SPIKE_REPORT.md` | what was measured, on which host, and what was not |

## Commands

```sh
python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/python -m unittest discover -s tests -t . -v        # scripted test double; real-model test skips
.venv/bin/python tools/check_sdk_copies.py [<Zairenkai-Sdk checkout>]
ZIE_LLAMA=<llama-completion> ZIE_MODEL=<gguf> .venv/bin/python -m unittest tests.test_real_model
.venv/bin/python -m zie --llama <llama-completion> --model <gguf> "cek kenapa HP panas"
PYTHON=.venv/bin/python tools/offline-proof.sh <llama-completion> <gguf>
.venv/bin/python tools/eval.py --llama <llama-completion> --model <gguf>
```

Licence: Apache-2.0 (`LICENSE`, `NOTICE`).
