# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""zie/grammar.py and registry/output.gbnf: the grammar the on-device runner samples under."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

from zie import agent, grammar
from zie.registry import ToolRegistry
from zie.runtime import ZieRunRuntime

ROOT = Path(__file__).resolve().parent.parent


class GrammarTest(unittest.TestCase):
    def test_committed_grammar_is_what_the_registry_produces(self):
        r = subprocess.run([sys.executable, str(ROOT / "tools/gen_grammar.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_every_registered_tool_and_only_those(self):
        g = (ROOT / "registry/output.gbnf").read_text()
        for t in ToolRegistry.load().tools:
            self.assertIn(f'"\\"{t["id"]}\\""', g)
        self.assertNotIn("shell", g)
        # Key order is fixed and every string and whitespace run is bounded.
        self.assertIn('char{0,200}', g)
        self.assertIn("ws ::= [ \\t\\n]{0,8}", g)

    def test_integers_have_no_leading_zeros(self):
        self.assertEqual(grammar._bounded_int(100), '"0" | [1-9] | [1-9] [0-9] | "100"')
        self.assertEqual(grammar._bounded_int(9), '"0" | [1-9]')

    def test_unsupported_schemas_fail_closed(self):
        for bad in (
            {"type": "string"},  # unbounded
            {"type": "object", "properties": {"a": {"const": "x"}}, "required": [], "additionalProperties": False},
            {"type": "object", "properties": {}, "required": []},  # open object
            {"type": "number"},
            {"type": "array", "items": {"const": "x"}, "maxItems": 50},
            {"enum": [1, 2]},
        ):
            with self.assertRaises(grammar.UnsupportedSchema, msg=str(bad)):
                grammar.gbnf(bad)


@unittest.skipUnless(os.environ.get("ZIE_RUN") and os.environ.get("ZIE_MODEL"), "set ZIE_RUN (host zie-run) and ZIE_MODEL")
class ZieRunRealModelTest(unittest.TestCase):
    """The runner the app ships, built for the host, with the real model and the committed grammar."""

    def test_requests_map_to_registered_tools(self):
        reg = ToolRegistry.load()
        rt = ZieRunRuntime(Path(os.environ["ZIE_RUN"]), Path(os.environ["ZIE_MODEL"]), ROOT / "registry/output.gbnf")
        from zie.executor import FixtureReplayExecutor

        a = agent.Agent(rt, reg, FixtureReplayExecutor())
        turn = a.handle("Set FAS to performance mode please")
        self.assertIsNotNone(turn.plan, turn.rejected_reason)
        self.assertEqual([i["tool_id"] for i in turn.plan["invocations"]], ["fas.set_profile"])
        self.assertEqual(turn.plan["invocations"][0]["arguments"], {"profile": "performance"})
        self.assertIsNotNone(turn.preview)  # a system action waits for approval
        turn = a.handle("berapa suhu hp saya sekarang?")
        self.assertIsNotNone(turn.plan, turn.rejected_reason)
        self.assertIn("thermal.snapshot", [i["tool_id"] for i in turn.plan["invocations"]])


if __name__ == "__main__":
    unittest.main()
