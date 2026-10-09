from __future__ import annotations
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from control.model_execution.direct_sol_chat import build_request, DirectSolError
from control.model_execution.direct_sol_delivery import (
    context_for, delivery_status, enqueue_published_request, published_request,
)
from control.tampermonkey_multichat import continuation_manager as cm


class DirectSolDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bridge = self.root / "bridge"
        (self.bridge / "routes").mkdir(parents=True)
        (self.bridge / "outbox").mkdir()
        self.route = "SESSION-ROUTE-sol-test"
        (self.bridge / "routes" / (self.route + ".json")).write_text(json.dumps({
            "task_id": self.route, "chat_id": "chat-sol-test", "consumer_id": None,
        }))
        self.request = build_request(
            task_id="SOL-DELIVERY-TEST", phase="SOL_PROPOSAL", campaign_id="C1",
            candidate_id="X1", binding_sha256="b" * 64, prompt="complete governed prompt",
            delivery_route_task_id=self.route, created_at_utc="2026-10-09T00:00:00Z",
        )
        self.path = self.root / (self.request["task_id"] + ".json")
        self.path.write_text(json.dumps(self.request))
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.commit = "c" * 40

    def enqueue(self, **kwargs):
        return enqueue_published_request(
            request_path=self.path, request_sha256=self.sha, commit=self.commit,
            bridge_data=self.bridge, state_root=self.root / "delivery",
            continuation=cm, **kwargs,
        )

    def test_real_continuation_api_queues_once_after_restart(self):
        first = self.enqueue()
        second = self.enqueue()
        self.assertTrue(first["new_delivery_queued"])
        self.assertFalse(second["new_delivery_queued"])
        self.assertEqual(first["continuation_id"], second["continuation_id"])
        self.assertEqual(len(list((self.bridge / "outbox").glob("*.json"))), 1)
        event = json.loads(next((self.bridge / "outbox").glob("*.json")).read_text())
        self.assertIn("PREDICTION_DIRECT_SOL_HANDOFF_V1", event["message"])
        self.assertIn(self.commit, event["message"])
        self.assertIn(self.request["input_sha256"], event["message"])
        self.assertIn("MODEL_IDENTITY_UNAVAILABLE", event["message"])
        self.assertFalse(first["model_execution_proven"])
        self.assertEqual(first["model_status"], "WAITING_FOR_ACTUAL_SOL_RESULT")

    def test_transport_done_never_means_model_completed(self):
        for state in ("CONTINUE_QUEUED", "CONTINUE_SENT", "DONE_RECEIPT_CREATED", "DONE"):
            self.assertEqual(delivery_status(
                {"state": state}, model_result_present=False, now=20,
                created_at=10, deadline_seconds=30,
            ), "WAITING_FOR_ACTUAL_SOL_RESULT")

    def test_deadline_visible_even_after_transport_done(self):
        self.assertEqual(delivery_status(
            {"state": "DONE"}, model_result_present=False, now=40,
            created_at=10, deadline_seconds=30,
        ), "BLOCKED_NO_MODEL_RESULT")

    def test_result_presence_requires_separate_validation(self):
        self.assertEqual(delivery_status(
            {"state": "CONTINUE_SENT"}, model_result_present=True, now=11,
            created_at=10, deadline_seconds=30,
        ), "MODEL_RESULT_PRESENT_REQUIRES_VALIDATION")

    def test_wrong_publication_hash_does_not_enqueue(self):
        self.path.write_text(self.path.read_text() + " ")
        with self.assertRaisesRegex(DirectSolError, "PUBLICATION_HASH"):
            self.enqueue()
        self.assertFalse(list((self.bridge / "outbox").glob("*.json")))

    def test_wrong_input_hash_does_not_enqueue(self):
        self.request["prompt"] = "substituted prompt"
        self.path.write_text(json.dumps(self.request))
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(DirectSolError, "INPUT_HASH"):
            self.enqueue()
        self.assertFalse(list((self.bridge / "outbox").glob("*.json")))

    def test_route_mismatch_does_not_enqueue(self):
        p = self.bridge / "routes" / (self.route + ".json")
        p.write_text(json.dumps({"task_id": "wrong-route", "chat_id": "chat-sol-test"}))
        with self.assertRaisesRegex(DirectSolError, "ROUTE_BINDING"):
            self.enqueue()
        self.assertFalse(list((self.bridge / "outbox").glob("*.json")))

    def test_missing_route_fails_closed(self):
        (self.bridge / "routes" / (self.route + ".json")).unlink()
        with self.assertRaises(FileNotFoundError):
            self.enqueue()
        self.assertFalse(list((self.bridge / "outbox").glob("*.json")))

    def test_mutated_publication_under_same_task_conflicts(self):
        self.enqueue()
        self.commit = "d" * 40
        with self.assertRaisesRegex(ValueError, "RUNTIME_CONFLICT"):
            self.enqueue()
        self.assertEqual(len(list((self.bridge / "outbox").glob("*.json"))), 1)

    def test_crash_after_intent_and_continuation_before_enqueue(self):
        original = cm.enqueue_attempt
        def fail(**kwargs):
            raise RuntimeError("injected crash")
        cm.enqueue_attempt = fail
        try:
            with self.assertRaisesRegex(RuntimeError, "injected crash"):
                self.enqueue()
        finally:
            cm.enqueue_attempt = original
        recovered = self.enqueue()
        self.assertTrue(recovered["new_delivery_queued"])
        self.assertEqual(len(list((self.bridge / "outbox").glob("*.json"))), 1)

    def test_branch_reference_is_not_immutable(self):
        with self.assertRaisesRegex(DirectSolError, "IMMUTABLE_COMMIT"):
            published_request(self.path, expected_sha256=self.sha, commit="main")

    def test_worker_reported_block_is_not_retry(self):
        self.assertEqual(delivery_status(
            {"state": "BLOCKED_RECEIPT_CREATED"}, model_result_present=False,
            now=11, created_at=10, deadline_seconds=30,
        ), "BLOCKED_WORKER_OR_TRANSPORT")

    def test_unsafe_task_cannot_escape_directories(self):
        self.request["task_id"] = "../escape"
        with self.assertRaisesRegex(DirectSolError, "REFERENCE_INVALID"):
            context_for(self.request, commit=self.commit, request_sha256=self.sha)

    def test_elapsed_handoff_does_not_generate_new_delivery(self):
        first = self.enqueue()
        second = self.enqueue(now=first["deadline_at"] + 1)
        self.assertEqual(second["model_status"], "BLOCKED_NO_MODEL_RESULT")
        self.assertFalse(second["new_delivery_queued"])
        self.assertEqual(len(list((self.bridge / "outbox").glob("*.json"))), 1)

    def test_denied_continuation_is_explicit_capability_blocker(self):
        class Denied:
            def start_external_continuation(self, **kwargs):
                raise PermissionError("guard blocked runtime write")
        with self.assertRaisesRegex(
            DirectSolError, "DIRECT_SOL_CONTINUATION_CAPABILITY_UNAVAILABLE"
        ):
            enqueue_published_request(
                request_path=self.path, request_sha256=self.sha, commit=self.commit,
                bridge_data=self.bridge, state_root=self.root / "delivery",
                continuation=Denied(),
            )
        self.assertFalse(list((self.bridge / "outbox").glob("*.json")))
