from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from control.model_execution.direct_sol_chat import build_request, build_result, validate_result
from control.model_execution.patch_e106_gate import E106, hydrate, patch_gate, patch_runner


class DirectSolChatHappyPathTests(unittest.TestCase):
    def test_exact_sol_chat_result_binds(self):
        req = build_request(
            task_id="SOL-DIRECT-TEST-1",
            phase="SOL_BUILD",
            campaign_id="C1",
            candidate_id="X1",
            binding_sha256="b" * 64,
            prompt="bounded result",
            delivery_route_task_id="SESSION-ROUTE-controller",
            created_at_utc="2026-10-07T10:00:00Z",
        )
        result = build_result(
            req,
            worker_route_task_id="SESSION-ROUTE-worker",
            final="ok",
            started_at_utc="2026-10-07T10:01:00Z",
            finished_at_utc="2026-10-07T10:02:00Z",
        )
        self.assertEqual(validate_result(req, result), result)
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertEqual(result["experience"], "CHAT")


class E106DirectRoutingPatchTests(unittest.TestCase):
    def test_hydrated_runner_routes_sol_direct_and_blocks_legacy_sol(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            source = root / E106
            target = tmp / E106
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

            hydrate(tmp)
            patch_gate(tmp)
            patch_runner(tmp)

            runner = (tmp / "control/jobs/full_a2z_governed_v4.py").read_text(encoding="utf-8")
            gate = (tmp / "control/codex_supervisor/experiment_gate.py").read_text(encoding="utf-8")

            self.assertIn('raise ValueError("DIRECT_SOL_REQUIRED")', runner)
            self.assertIn('direct_sol_request(repo, overlay, "SOL_BUILD"', runner)
            self.assertIn('direct_sol_request(repo, overlay, "SOL_PROPOSAL"', runner)
            self.assertIn('prepare_review(repo, overlay, "POSTBUILD"', runner)
            self.assertIn("worker_policy_error(worker, phase)", gate)

            compile(runner, "full_a2z_governed_v4.py", "exec")
            compile(gate, "experiment_gate.py", "exec")


if __name__ == "__main__":
    unittest.main()
