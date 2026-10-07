from __future__ import annotations

import unittest

from control.model_execution.direct_sol_chat import build_request, build_result, validate_result


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


if __name__ == "__main__":
    unittest.main()
