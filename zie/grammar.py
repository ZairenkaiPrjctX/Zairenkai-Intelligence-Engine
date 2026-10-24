# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""JSON Schema → GBNF for the registry's output schema, the grammar zie-run samples under.

Only the shapes ToolRegistry.output_schema() produces are supported; anything else raises, so a
registry change cannot silently loosen the grammar:

- object with additionalProperties false: every property, in schema order, all required;
- string with maxLength; enum and const of strings; integer with minimum 0 and maximum ≤ 999;
- array with maxItems whose items are an anyOf of the above objects.

The grammar fixes key order and bounds every string and whitespace run, so the output is short
and always parses as JSON of the schema's shape; the agent still re-validates it.
"""
from __future__ import annotations

import json
from typing import Any

WS = 'ws ::= [ \\t\\n]{0,8}'
CHAR = 'char ::= [^"\\\\\\x7F\\x00-\\x1F] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F]{4})'


class UnsupportedSchema(ValueError):
    pass


def _lit(s: str) -> str:
    """A GBNF literal for the JSON text of string s (with its quotes)."""
    j = json.dumps(s, ensure_ascii=False)
    return '"' + j.replace("\\", "\\\\").replace('"', '\\"') + '"'


class _Builder:
    def __init__(self) -> None:
        self.rules: dict[str, str] = {}

    def rule(self, name: str, body: str) -> str:
        if self.rules.get(name, body) != body:
            raise UnsupportedSchema(f"rule {name} defined twice")
        self.rules[name] = body
        return name

    def value(self, name: str, s: dict[str, Any]) -> str:
        if "const" in s:
            if set(s) != {"const"} or not isinstance(s["const"], str):
                raise UnsupportedSchema(f"{name}: const must be a lone string")
            return self.rule(name, _lit(s["const"]))
        if "enum" in s:
            if set(s) != {"enum"} or not s["enum"] or not all(isinstance(v, str) for v in s["enum"]):
                raise UnsupportedSchema(f"{name}: enum must be a lone list of strings")
            return self.rule(name, " | ".join(_lit(v) for v in s["enum"]))
        if "anyOf" in s:
            if set(s) != {"anyOf"}:
                raise UnsupportedSchema(f"{name}: anyOf must stand alone")
            alts = [self.value(f"{name}-{i}", a) for i, a in enumerate(s["anyOf"])]
            return self.rule(name, " | ".join(alts))
        t = s.get("type")
        if t == "string":
            if set(s) - {"type", "maxLength"} or not isinstance(s.get("maxLength"), int):
                raise UnsupportedSchema(f"{name}: strings need a maxLength and nothing else")
            return self.rule(name, f'"\\"" char{{0,{s["maxLength"]}}} "\\""')
        if t == "integer":
            if set(s) != {"type", "minimum", "maximum"} or s["minimum"] != 0 or not 0 < s["maximum"] <= 999:
                raise UnsupportedSchema(f"{name}: integers need minimum 0 and a maximum up to 999")
            return self.rule(name, _bounded_int(s["maximum"]))
        if t == "array":
            if set(s) != {"type", "maxItems", "items"} or not 0 < s["maxItems"] <= 8:
                raise UnsupportedSchema(f"{name}: arrays need maxItems (1-8) and items")
            item = self.value(f"{name}-item", s["items"])
            more = s["maxItems"] - 1
            tail = f' ("," ws {item}){{0,{more}}}' if more else ""
            return self.rule(name, f'"[" ws ({item}{tail})? "]" ws')
        if t == "object":
            extra = set(s) - {"type", "additionalProperties", "required", "properties"}
            props = s.get("properties", {})
            if extra or s.get("additionalProperties") is not False or set(s.get("required", [])) != set(props):
                raise UnsupportedSchema(f"{name}: objects must be closed with every property required")
            parts = []
            for i, (key, sub) in enumerate(props.items()):
                v = self.value(f"{name}-{key.replace('_', '-')}", sub)
                parts.append(("" if i == 0 else '"," ws ') + f"{_lit(key)} ws \":\" ws {v} ws")
            body = '"{" ws ' + " ".join(parts) + (" " if parts else "") + '"}" ws'
            return self.rule(name, body)
        raise UnsupportedSchema(f"{name}: unsupported schema {sorted(s)}")


def _bounded_int(maximum: int) -> str:
    """0..maximum without leading zeros, as alternatives by digit count."""
    alts = ['"0"']
    for digits in range(1, len(str(maximum)) + 1):
        lo, hi = (1 if digits == 1 else 10 ** (digits - 1)), min(maximum, 10 ** digits - 1)
        if lo > hi:
            continue
        if hi == 10 ** digits - 1:
            alts.append("[1-9]" + " [0-9]" * (digits - 1))
        else:
            alts.extend(f'"{n}"' for n in range(lo, hi + 1))
    return " | ".join(alts)


def gbnf(schema: dict[str, Any]) -> str:
    b = _Builder()
    top = b.value("out", schema)
    lines = [f"root ::= ws {top}"] + [f"{k} ::= {v}" for k, v in b.rules.items()] + [WS, CHAR]
    return "\n".join(lines) + "\n"
