#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Airplane-mode proof on a Linux host: run one complete agent turn with the whole process tree
# (Python agent and llama.cpp) inside a new, empty network namespace, after showing that the
# namespace has no usable interface and that an outbound connection fails there.
#
# Usage: tools/offline-proof.sh <llama-completion> <model.gguf> [utterance]
# Needs unshare(1) with permission to create a network namespace (root, or user namespaces).
set -euo pipefail
[ $# -ge 2 ] || { echo "usage: $0 <llama-completion> <model.gguf> [utterance]" >&2; exit 2; }
llama=$1 model=$2 utterance=${3:-"cek kenapa HP panas saat main game"}
python=${PYTHON:-python3}
cd "$(dirname "$0")/.."
# The inner script is single-quoted on purpose: it expands inside the new namespace.
# shellcheck disable=SC2016
exec unshare -n -- env LLAMA="$llama" MODEL="$model" UTTERANCE="$utterance" PY="$python" bash -c '
  set -euo pipefail
  echo "== interfaces in this namespace (only lo, down):"
  ip -brief link 2>/dev/null || cat /proc/net/dev
  echo "== outbound connection attempt:"
  if "$PY" -c "import socket; socket.create_connection((\"1.1.1.1\", 443), timeout=3)" 2>/dev/null; then
    echo "FAIL: the namespace has network access" >&2; exit 1
  fi
  echo "refused (no route): ok"
  echo "== one agent turn:"
  "$PY" -m zie --llama "$LLAMA" --model "$MODEL" "$UTTERANCE"
'
