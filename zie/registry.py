# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""The closed ToolRegistry. Loaded once from registry/tools.json, validated against the SDK
schema; the model can neither add nor rename tools."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from . import contracts

DEFAULT = contracts.ROOT / "registry" / "tools.json"


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class ToolRegistry:
    tools: tuple[dict[str, Any], ...]

    @classmethod
    def load(cls, path: Path = DEFAULT) -> "ToolRegistry":
        tools = contracts.load(path)
        errs = contracts.errors("sdk/local-ai/tool-registry.schema.json", tools)
        ids = [t["id"] for t in tools] if not errs else []
        errs += [f"duplicate tool id {i}" for i in sorted({i for i in ids if ids.count(i) > 1})]
        for t in tools if not errs else []:
            Draft202012Validator.check_schema(t["parameters"])
            if t["parameters"].get("additionalProperties") is not False:
                errs.append(f"{t['id']}: parameters must be a closed object")
        if errs:
            raise RegistryError("; ".join(errs))
        return cls(tuple(tools))

    def get(self, tool_id: str) -> dict[str, Any] | None:
        return next((t for t in self.tools if t["id"] == tool_id), None)

    def argument_errors(self, tool_id: str, arguments: Any) -> list[str]:
        tool = self.get(tool_id)
        if tool is None:
            return [f"unknown tool {tool_id}"]
        return [e.message for e in Draft202012Validator(tool["parameters"]).iter_errors(arguments)]

    def output_schema(self) -> dict[str, Any]:
        """The JSON Schema the model's output is constrained to: each call names a registered tool
        with that tool's own parameter schema. It is also re-checked after generation."""
        calls = [{"type": "object", "additionalProperties": False, "required": ["tool", "arguments"],
                  "properties": {"tool": {"const": t["id"]}, "arguments": t["parameters"]}} for t in self.tools]
        return {
            "type": "object", "additionalProperties": False,
            "required": ["language", "goal", "confidence_percent", "calls", "clarification"],
            "properties": {
                "language": {"enum": ["id", "en", "other"]},
                "goal": {"type": "string", "maxLength": 200},
                "confidence_percent": {"type": "integer", "minimum": 0, "maximum": 100},
                "calls": {"type": "array", "maxItems": 3, "items": {"anyOf": calls}},
                "clarification": {"type": "string", "maxLength": 200},
            },
        }
