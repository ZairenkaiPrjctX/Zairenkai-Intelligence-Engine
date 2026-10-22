# ADR 0001: Local model runtime for the Phase A spike: llama.cpp; LiteRT-LM stays the Android candidate

Status: accepted for the spike (2026-10-22). The production runtime is decided in Phase B, on a
real device.

## Constraints (maintainer brief, 2026-10-22)

- Inference on the device, offline. No remote AI API, ever; model download is a separate,
  user-initiated step that uploads nothing.
- Structured tool calling only: the model emits typed requests against a closed registry, never
  code or shell.
- Every privileged action goes through Zairenkai-Core, which re-validates it.

## Candidates audited

| | llama.cpp | LiteRT-LM |
|---|---|---|
| Source | ggml-org/llama.cpp, tag `b11500` = `097f5b5332f46559f1ee11d9d64e48a5065b2989` (2026-10-08) | google-ai-edge/LiteRT-LM, tag `v0.18.1` = `bda624851d74be34d4e1f7fac1fc4155939539c7` (2026-10-20) |
| Licence (LICENSE at that commit) | MIT, "The ggml authors" | Apache-2.0 |
| Model format | GGUF (many open-weight models, own quantizations) | `.litertlm` (models converted by Google AI Edge; fewer choices) |
| Structured output | JSON Schema → grammar-constrained sampling (`--json-schema`): the model cannot emit a token outside the schema | "Tool Use" / function-calling API (README); constrained decoding not verified in this audit |
| Android API | C/C++ library; JNI binding to write (docs/android.md upstream) | Kotlin API (`kotlin/java/com/google/ai/edge/litertlm/`: `Conversation`, `Config`, `Benchmark`) |
| Accelerators | CPU everywhere; Vulkan/OpenCL backends vary by driver | CPU, GPU, NPU (README), per device |
| Built and run here | **yes**: CPU build on Linux x86_64, CMake/Ninja, no curl | no (Bazel toolchain; not attempted in the spike) |

Reference app (not a dependency): google-ai-edge/gallery `8f5f2a0bdb7c81693384dbdecbabec9b1e8d7f4e`
(2026-10-13), Apache-2.0: on-device model management and "Mobile Actions" with LiteRT-LM.

## Decision

- The spike uses **llama.cpp `b11500`** on CPU, because grammar-constrained JSON output makes the
  closed registry enforceable at generation time, the build is reproducible from source with the
  existing toolchain, and the licence is MIT.
- The model is **Qwen2.5-0.5B-Instruct GGUF q4_0** (`Qwen/Qwen2.5-0.5B-Instruct-GGUF` revision
  `9217f5db79a29953eb74d5343926648285ec7e67`, Apache-2.0, 428,730,208 bytes, SHA-256
  `7671c0c3…ed6`; `models/qwen2.5-0.5b-instruct-q4_0.json`). It is not stored in Git.
- The runtime sits behind `LocalModelRuntime` (`zie/runtime.py`) so LiteRT-LM can be added
  without touching the agent loop.
- The spike is Python (agent loop, validation against the Zairenkai-Sdk schemas). It is a
  feasibility harness, not the product: the on-device implementation language (Kotlin in the
  app process, or a native library) is a Phase B decision together with the runtime.

## What must happen before Phase B picks the production runtime

1. Build llama.cpp and LiteRT-LM for arm64-v8a and run the same evaluation on at least one
   real device per SoC family available (Qualcomm, MediaTek, Exynos, Tensor): load time, tokens/s,
   peak memory, thermal effect, tool-call accuracy.
2. Choose the model by measurement: 0.5B passed 9 of 16 spike cases (docs/SPIKE_REPORT.md).
3. Record model licences for weights, tokenizer and configuration separately in a ModelManifest.

## Consequences

- No inference code ships to devices from this change.
- The Python spike depends on `jsonschema` (hash-locked) and an external llama.cpp binary and
  model file provided by the developer; CI runs the agent tests with a scripted test double.
