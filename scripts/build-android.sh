#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
#
# Builds the Zairenkai Local AI component for Android: zie-run (runtime/zie_run.cpp) against
# llama.cpp's core libraries at the commit runtime/llama.cpp.json pins, for arm64-v8a and x86_64,
# API 29, statically linked C++ runtime, 16 KB-aligned LOAD segments. Each binary is checked:
#   - it imports no networking function (socket, connect, getaddrinfo, ...): inference cannot
#     reach the network, whatever the model emits;
#   - it needs only libc, libm, libdl and liblog.
# Output: dist/zairenkai-intelligence/ with bin/<abi>/zie-run, the closed tool registry and its
# grammar, the model manifest, licences (llama.cpp MIT) and component.json (SHA-256 per file).
#
# Usage: ANDROID_NDK_HOME=<ndk r27d> scripts/build-android.sh
#   LLAMA_CPP_SRC=<checkout>  use an existing llama.cpp checkout (its HEAD must be the pinned commit)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
: "${ANDROID_NDK_HOME:?set ANDROID_NDK_HOME to an Android NDK (r27d)}"
NDK=$ANDROID_NDK_HOME
LLVM="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin"
ABIS="arm64-v8a x86_64"
OUT="$ROOT/dist/zairenkai-intelligence"

field() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' runtime/llama.cpp.json "$1"; }
COMMIT=$(field commit)
TAG=$(field tag)
URL=$(field url)

SRC=${LLAMA_CPP_SRC:-$ROOT/build/llama.cpp}
if [ -z "${LLAMA_CPP_SRC:-}" ]; then
  mkdir -p "$SRC"
  [ -d "$SRC/.git" ] || { git init -q "$SRC"; git -C "$SRC" remote add origin "$URL"; }
  git -C "$SRC" fetch -q --depth 1 origin "$COMMIT"
  git -C "$SRC" -c advice.detachedHead=false checkout -q --force FETCH_HEAD
fi
[ "$(git -C "$SRC" rev-parse HEAD)" = "$COMMIT" ] || { echo "llama.cpp at $SRC is not $COMMIT" >&2; exit 1; }

python3 tools/gen_grammar.py --check >/dev/null 2>&1 || {
  # The check needs jsonschema; without it, at least require the committed grammar.
  [ -s registry/output.gbnf ] || { echo "registry/output.gbnf missing" >&2; exit 1; }
}

rm -rf "$OUT"
mkdir -p "$OUT/registry" "$OUT/models" "$OUT/licenses/llama.cpp"
for abi in $ABIS; do
  build="$ROOT/build/android-$abi"
  cmake -S runtime -B "$build" -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$NDK/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI="$abi" -DANDROID_PLATFORM=android-29 -DANDROID_STL=c++_static \
    -DCMAKE_BUILD_TYPE=Release -DLLAMA_CPP_SRC="$SRC" -DZIE_LLAMA_TAG="$TAG" \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,-z,max-page-size=16384 -Wl,--build-id=none" >/dev/null
  cmake --build "$build" --target zie-run -j "$(nproc)" >/dev/null
  bin="$OUT/bin/$abi/zie-run"
  mkdir -p "$(dirname "$bin")"
  "$LLVM/llvm-strip" -o "$bin" "$build/zie-run"
  chmod 0755 "$bin"

  net=$("$LLVM/llvm-nm" -D --undefined-only "$bin" | awk '{print $NF}' | sed 's/@.*//' |
        grep -xE 'socket|connect|bind|listen|accept4?|getaddrinfo|gethostbyname2?|getnameinfo|sendto|recvfrom|send|recv|sendmsg|recvmsg|socketpair|inet_(pton|ntop|addr)' || true)
  [ -z "$net" ] || { echo "$abi: zie-run imports networking functions: $net" >&2; exit 1; }
  needed=$("$LLVM/llvm-readelf" -d "$bin" | sed -n 's/.*NEEDED.*\[\(.*\)\]/\1/p' | sort | tr '\n' ' ')
  for lib in $needed; do
    case "$lib" in libc.so|libm.so|libdl.so|liblog.so) ;; *) echo "$abi: unexpected dependency $lib" >&2; exit 1 ;; esac
  done
  if "$LLVM/llvm-readelf" -lW "$bin" | awk '$1=="LOAD" && $NF!="0x4000" {bad=1} END {exit !bad}'; then
    echo "$abi: a LOAD segment is not 16 KB aligned" >&2; exit 1
  fi
  echo "$abi: zie-run ok (no network imports; needs: $needed)"
done

cp registry/tools.json registry/output.gbnf "$OUT/registry/"
cp models/*.json "$OUT/models/"
cp LICENSE NOTICE "$OUT/"
cp "$SRC/LICENSE" "$OUT/licenses/llama.cpp/LICENSE"

python3 - "$OUT" "$(git rev-parse HEAD)" "$COMMIT" "$TAG" <<'PY'
import hashlib, json, os, sys
out, commit, llama, tag = sys.argv[1:5]
files = {}
for d, _, names in os.walk(out):
    for n in sorted(names):
        p = os.path.join(d, n)
        rel = os.path.relpath(p, out)
        files[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
doc = {
    "format": 1, "component": "zairenkai-intelligence", "repository": "ZairenkaiPrjctX/Zairenkai-Intelligence-Engine",
    "version": "0.1.0", "commit": commit, "target": "android (arm64-v8a, x86_64), API 29",
    "llama_cpp": {"commit": llama, "tag": tag, "license": "MIT"},
    "files": dict(sorted(files.items())),
}
json.dump(doc, open(os.path.join(out, "component.json"), "w"), indent=2)
print(f"{out}: {len(files)} files")
PY
