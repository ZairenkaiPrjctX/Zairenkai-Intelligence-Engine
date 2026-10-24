# ADR 0002: The on-device runner: zie-run on llama.cpp's core libraries

Status: accepted (2026-10-23). Supersedes the "no inference code ships to devices" consequence of
ADR 0001; the runtime choice itself (llama.cpp, CPU) is unchanged.

## Decision

The Zairenkai app runs **zie-run** (`runtime/zie_run.cpp`, Apache-2.0), a small program linked
against llama.cpp's **core** libraries only (`llama`, `ggml`; MIT; `runtime/llama.cpp.json` pins
`b11500` = `097f5b53`). It loads the GGUF model, reads the prompt from a file and samples greedily
under `registry/output.gbnf`, printing only the generated JSON.

- **Why not `llama-completion`:** llama.cpp's `common` library always links cpp-httplib (model
  download), so every stock tool carries an HTTP client. zie-run links no networking code;
  `scripts/build-android.sh` fails if the binary imports any socket, connect or name-resolution
  function, or needs a library other than libc, libm, libdl and liblog.
- **Why a precomputed grammar:** the JSON-Schema-to-grammar converter lives in `common` too.
  `zie/grammar.py` produces the grammar from `ToolRegistry.output_schema()` for exactly the schema
  shapes the registry uses, failing on anything else; `registry/output.gbnf` is generated and
  checked by `tools/gen_grammar.py --check`. The agent re-validates every output anyway.
- **No network namespace on Android:** an app cannot `unshare -n`. The guarantee there is the
  binary's import table (above) and the agent, which opens no connection during a turn. On a
  Linux host `ZieRunRuntime` still uses `unshare -n`.
- **CPU baseline:** arm64-v8a (ARMv8.0, no DOTPROD) and x86_64, API 29, statically linked C++
  runtime, 16 KB-aligned segments: one binary runs on every supported device. Faster CPU
  variants wait for measurements on devices.

## Consequences

- `scripts/build-android.sh` emits `dist/zairenkai-intelligence/` (runner per ABI, registry,
  grammar, model manifest, licences, `component.json`); Zairenkai-App's build-components.sh
  packages it. The model is not packaged: the app downloads it on the user's request and checks
  it against the manifest's SHA-256 and size.
- Verified on a Linux x86_64 host with the real model (`tests/test_grammar.py`,
  `ZieRunRealModelTest`). **Unverified** on a device: load time, memory and speed per SoC.
