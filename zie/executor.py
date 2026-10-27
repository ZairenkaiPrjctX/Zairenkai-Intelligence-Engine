# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Executors for read-only tools.

The spike has no device and no Core client. FixtureReplayExecutor answers read-only tools with
outputs the real binaries produced on a Linux host (fixtures/replay/, copied from Zairenkai-Sdk
with their SHA-256). Every result says so; nothing here is live device data. System tools are
never executed by an executor: they need a preview, approval and Zairenkai-Core.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from . import contracts

REPLAY = contracts.ROOT / "fixtures" / "replay"


class ReadOnlyExecutor(Protocol):
    label: str

    def run(self, tool_id: str, arguments: dict[str, Any]) -> Any: ...


class ToolUnavailable(RuntimeError):
    pass


@dataclass
class FixtureReplayExecutor:
    label: str = "fixture replay (captured on a Linux host; not live device data)"

    FILES = {
        "core.health": ("core-health.json", "result"),
        "core.capabilities": ("core-capabilities.json", "result"),
        "fas.status": ("fas-status.json", None),
        "thermal.snapshot": ("zthermal-snapshot-host.json", None),
        "tuning.telemetry": ("tuning-telemetry.json", None),
    }

    def run(self, tool_id: str, arguments: dict[str, Any]) -> Any:
        if tool_id not in self.FILES:
            raise ToolUnavailable(f"no read-only executor for {tool_id}")
        name, key = self.FILES[tool_id]
        doc = contracts.load(REPLAY / name)
        return doc[key] if key else doc
