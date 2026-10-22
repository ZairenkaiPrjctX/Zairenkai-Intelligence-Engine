# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Zairenkai Local AI, Phase A spike: local model → typed IntentPlan → closed ToolRegistry.

Nothing here talks to a remote model, and nothing here holds root: system tools only produce a
preview; executing them belongs to Zairenkai-Core (Phase C).
"""

ROOT_MARKER = "contracts/sources.json"
