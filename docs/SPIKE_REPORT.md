# Phase A spike report (2026-10-22)

What was shown, on which machine, and what was not. Host: Linux x86_64 cloud container, 4
threads used, CPU only. **No Android device was used.**

## Setup (reproducible)

```sh
git init llama.cpp && git -C llama.cpp fetch --depth 1 https://github.com/ggml-org/llama.cpp.git refs/tags/b11500
git -C llama.cpp checkout FETCH_HEAD          # 097f5b5332f46559f1ee11d9d64e48a5065b2989
cmake -S llama.cpp -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DGGML_NATIVE=OFF
cmake --build build --target llama-completion
curl -L -o qwen2.5-0.5b-instruct-q4_0.gguf \
  https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/9217f5db79a29953eb74d5343926648285ec7e67/qwen2.5-0.5b-instruct-q4_0.gguf
python3 -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock
```

`python -m zie` checks the model's SHA-256 and size against `models/…json` before loading it.

## Results

| Acceptance item | Command | Result |
|---|---|---|
| One offline model load | `python -m zie --llama build/bin/llama-completion --model qwen…gguf "cek kenapa HP panas saat main game"` | exit 0; 5.4 s wall time for the whole turn (load + generation); peak child RSS 729 MiB (Python + llama.cpp, `resource.getrusage`) |
| One typed tool call | same run | IntentPlan valid against the SDK schema; invocations `thermal.snapshot`, `fas.status`, both `completed` (fixture replay) |
| Airplane-mode proof | `tools/offline-proof.sh build/bin/llama-completion qwen…gguf` | the whole agent ran in a new network namespace: only `lo`, no traffic; outbound connect refused; turn completed; `network_attempts: []` |
| In-process guard | `tests/test_agent.py` (`Offline`) | every connect and name lookup blocked and recorded; a whole turn records none |
| Fail-closed parsing | `tests/test_agent.py` (`FailClosed`) | malformed JSON, unknown tool, extra field, bad argument, too many calls, runtime missing, chat-template injection: no plan, no action |
| System actions | `tests/test_agent.py` (`Planning`) | `fas.set_profile` only yields an ActionPreview; an approval is reported `rejected` (`core_client_not_implemented`), never applied |
| Real-model test | `ZIE_LLAMA=… ZIE_MODEL=… python -m unittest tests.test_real_model` | passed (4.8 s) |
| Bilingual evaluation (16 synthetic prompts) | `tools/eval.py … --out eval/results-2026-10-22-qwen2.5-0.5b-q4_0-x86_64.json` | **9/16 passed**; language field correct **2/16**; network attempts 0 |

### Evaluation detail

Misses: three Indonesian/English health or status questions produced no tool call; "what can
Zairenkai control" picked thermal and FAS status instead of `core.capabilities`; "what profile is
FAS using" asked for `fas.set_profile` instead of `fas.status`; "disable thermal throttling"
asked for `thermal.snapshot` and `fas.set_profile`. In every case a system tool only produced a
preview awaiting explicit approval; nothing was executed. The `clarification` text the model
wrote is often irrelevant, and its self-reported confidence was 0 in the first run: neither can
be shown to a user as is.

Conclusion: the pipeline works offline and enforces the closed registry; a 0.5B model is **not
accurate enough** to route requests alone. Phase B compares larger models and a deterministic
keyword router as a fallback, on devices.

## Not shown

- Anything on Android: no ARM build, no device memory/thermal/battery measurement, no NPU/GPU.
- LiteRT-LM was audited, not built or run.
- No Core client: system actions stop at the preview.
- No safety evaluation of the model (`safety_evaluation: not_evaluated`).
