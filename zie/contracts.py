# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""The Zairenkai-Sdk schemas copied into contracts/sdk/, resolvable by $id without a network."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT / "contracts" / "sdk"
BASE = "https://zairenkaiprjctx.github.io/schemas/"


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def registry() -> Registry:
    resources = []
    for p in sorted(SDK.rglob("*.schema.json")):
        s = load(p)
        Draft202012Validator.check_schema(s)
        resources.append((s["$id"], Resource.from_contents(s)))
    return Registry().with_resources(resources)


def errors(schema_id: str, document: Any) -> list[str]:
    """Validation errors of `document` against the schema with this $id (absolute or relative to BASE)."""
    sid = schema_id if schema_id.startswith("https://") else BASE + schema_id
    v = Draft202012Validator({"$ref": sid}, registry=registry())
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(document)]
