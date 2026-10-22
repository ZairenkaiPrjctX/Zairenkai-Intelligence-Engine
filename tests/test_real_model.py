# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""One real offline turn with the pinned model. Runs only when ZIE_LLAMA and ZIE_MODEL point at
the llama.cpp binary and the model file (docs/SPIKE_REPORT.md); otherwise it is skipped and says
why. It never downloads anything."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from zie import contracts
from zie.__main__ import verify_model
from zie.agent import Agent
from zie.executor import FixtureReplayExecutor
from zie.netguard import no_network
from zie.registry import ToolRegistry
from zie.runtime import LlamaCppRuntime

LLAMA, MODEL = os.environ.get("ZIE_LLAMA"), os.environ.get("ZIE_MODEL")


@unittest.skipUnless(LLAMA and MODEL, "ZIE_LLAMA / ZIE_MODEL not set: no local model on this machine")
class RealModel(unittest.TestCase):
    def test_one_offline_turn_yields_a_valid_plan_and_a_typed_tool_call(self):
        model = Path(MODEL)
        verify_model(model, contracts.ROOT / "models" / "qwen2.5-0.5b-instruct-q4_0.json")
        agent = Agent(LlamaCppRuntime(Path(LLAMA), model), ToolRegistry.load(), FixtureReplayExecutor())
        attempts: list[str] = []
        with no_network(attempts):
            turn = agent.handle("cek kenapa HP panas saat main game")
        self.assertEqual([], attempts)
        self.assertIsNotNone(turn.plan, turn.rejected_reason)
        self.assertEqual([], contracts.errors("sdk/local-ai/intent-plan.schema.json", turn.plan))
        self.assertTrue(turn.plan["invocations"], "the model called no tool")
        for r in turn.results:
            self.assertEqual([], contracts.errors("sdk/local-ai/execution-result.schema.json", r))


if __name__ == "__main__":
    unittest.main()
