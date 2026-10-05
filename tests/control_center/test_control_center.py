from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "control/control_center/server.py"
spec = importlib.util.spec_from_file_location("prediction_control_center_server", SERVER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


class ControlCenterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="prediction-control-center-test-")
        tmp_path = Path(self._tmp.name)
        repo = tmp_path / "repo"
        state = tmp_path / "state"
        (repo / "knowledge/candidates").mkdir(parents=True)
        (repo / "knowledge/runs/agent_packets").mkdir(parents=True)
        (repo / "knowledge/manual_scout_seeds").mkdir(parents=True)
        (repo / "knowledge/research").mkdir(parents=True)
        (repo / "control/control_center").mkdir(parents=True)
        (repo / "control/build_log/events").mkdir(parents=True)
        write_json(
            repo / "control/build_log/events/20261001T090000Z-W-1-PLAN.json",
            {
                "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
                "event_id": "20261001T090000Z-W-1-PLAN",
                "work_item_id": "W-1",
                "created_at_utc": "2026-10-01T09:00:00Z",
                "event_type": "PLAN",
                "work_item_status": "OPEN",
                "outcome": "PLANNED",
                "title": "Shared test work",
                "objective": "Prove one shared objective across sessions.",
                "summary": "Work item created.",
                "why": "Need shared continuity.",
                "next_action": "Run the first attempt.",
                "session_route_task_id": "SESSION-A",
                "task_ids": [],
                "commits": [],
                "evidence_refs": [],
                "tags": ["test"],
                "parent_event_id": None,
                "first_incomplete_step": "First attempt.",
            },
        )
        write_json(
            repo / "control/build_log/events/20261001T100000Z-W-1-FAIL.json",
            {
                "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
                "event_id": "20261001T100000Z-W-1-FAIL",
                "work_item_id": "W-1",
                "created_at_utc": "2026-10-01T10:00:00Z",
                "event_type": "RESULT",
                "work_item_status": "IN_PROGRESS",
                "outcome": "FAIL",
                "title": "Shared test work",
                "objective": "Prove one shared objective across sessions.",
                "summary": "First attempt failed.",
                "why": "Synthetic failure.",
                "next_action": "Continue at the first incomplete step.",
                "session_route_task_id": "SESSION-B",
                "task_ids": ["TASK-FAIL"],
                "commits": [],
                "evidence_refs": ["synthetic"],
                "tags": ["test"],
                "parent_event_id": "20261001T090000Z-W-1-PLAN",
                "first_incomplete_step": "Verification.",
            },
        )
        write_json(
            repo / "control/control_center/lifecycle_status.json",
            {
                "schema": "PREDICTION_CONTROL_CENTER_LIFECYCLE_V1",
                "updated_at": "2026-10-05",
                "full_chain_status": "NOT_PROVEN",
                "full_chain_label": "Volledige A→Z-keten nog niet bewezen",
                "next_required": "Bewijs één volledige actuele A→Z-run.",
                "invariant": "NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL",
                "stages": [
                    {
                        "id": "scout",
                        "label": "Verkenner",
                        "subtitle": "kansen vinden",
                        "state": "WORKING_COMPONENT",
                        "detail": "Scoutcomponent werkt.",
                    },
                    {
                        "id": "measurement",
                        "label": "Tests en meting",
                        "subtitle": "pas na Astra-goedkeuring",
                        "state": "PENDING_E2E",
                        "detail": "Volledige doorgang nog bewijzen.",
                    },
                ],
            },
        )

        write_json(
            repo / "knowledge/candidates/C-1.json",
            {
                "candidate_id": "C-1",
                "created_at": "2026-10-01T10:00:00Z",
                "updated_at": "2026-10-01T12:00:00Z",
                "hypothesis": "Late market pricing may lag settlement reality.",
                "lane": "microstructure",
                "phase": "SHADOW",
                "queue_status": "RUNNING",
                "decision": "UNPROVEN",
                "scientific_status": "NO_PROVEN_EDGE",
                "gates": {"mechanism": "PASS", "shadow": "PENDING"},
                "evidence_refs": ["knowledge/runs/R-1.json"],
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
            },
        )
        write_json(
            repo / "knowledge/runs/R-1.json",
            {
                "run_id": "R-1",
                "started_at": "2026-10-01T11:00:00Z",
                "status": "COMPLETED",
                "decision": "NO_PROVEN_EDGE",
                "candidate_id": "C-1",
                "agents": {"scout": "COMPLETED", "research_director": "COMPLETED"},
            },
        )
        write_json(
            repo / "knowledge/runs/agent_packets/R-1/scout.json",
            {"run_id": "R-1", "agent_id": "scout", "finding": "candidate"},
        )
        (repo / "knowledge/manual_scout_seeds/old-idea.md").write_text(
            "# Old idea\nA historical idea that predates canonical candidate records.",
            encoding="utf-8",
        )
        (repo / "knowledge/research/legacy-note.md").write_text(
            "# Legacy research",
            encoding="utf-8",
        )

        model = mod.ControlCenterModel(repo, state)
        model.command_state = tmp_path / "command_state"
        model.executor_state = tmp_path / "executor_state"
        model.mirror_root = tmp_path / "mirror_root"
        model.bus_repo = tmp_path / "bus_repo"
        model.bridge_data = tmp_path / "bridge_data"
        model.sync_request_root = state / "sync_requests"
        model.command_state.mkdir()
        model.executor_state.mkdir()
        (model.bridge_data / "sent").mkdir(parents=True)
        (model.bridge_data / "inflight").mkdir()
        (model.bridge_data / "outbox").mkdir()
        (model.bridge_data / "routes").mkdir()
        self.model = model

    def tearDown(self):
        self._tmp.cleanup()

    def test_snapshot_includes_current_and_legacy_ideas(self):
        snapshot = self.model.build_snapshot(force=True)
        ids = {x["candidate_id"] for x in snapshot["candidates"]}
        self.assertIn("C-1", ids)
        self.assertTrue(any(x.startswith("LEGACY-SEED-") for x in ids))
        self.assertEqual(snapshot["counts"]["candidates"], 2)
        self.assertEqual(snapshot["counts"]["legacy_candidates"], 1)
        self.assertEqual(snapshot["edge_state"], "NO_PROVEN_EDGE")
        self.assertEqual(snapshot["lifecycle"]["full_chain_status"], "NOT_PROVEN")
        self.assertEqual(snapshot["lifecycle"]["stages"][0]["state"], "WORKING_COMPONENT")
        self.assertEqual(snapshot["build_log"]["counts"]["work_items"], 1)
        self.assertEqual(snapshot["build_log"]["counts"]["in_progress"], 1)
        self.assertEqual(snapshot["counts"]["build_log_open"], 1)
        self.assertEqual(
            snapshot["legacy_artifacts"][0]["path"],
            "knowledge/research/legacy-note.md",
        )

    def test_candidate_journey_links_runs(self):
        detail = self.model.candidate_detail("C-1")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["linked_runs"][0]["run_id"], "R-1")
        stages = [x["stage"] for x in detail["timeline"]]
        self.assertIn("DISCOVERY", stages)
        self.assertIn("RUN", stages)
        self.assertIn("MECHANISM", stages)

    def test_run_detail_exposes_agent_packets(self):
        detail = self.model.run_detail("R-1")
        paths = {x["path"] for x in detail["artifacts"]}
        self.assertIn("knowledge/runs/R-1.json", paths)
        self.assertIn("knowledge/runs/agent_packets/R-1/scout.json", paths)

    def test_revive_is_immutable_new_request_and_preserves_safety(self):
        first = self.model.request_revive("C-1", "retry under current gates")
        second = self.model.request_revive("C-1")
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertEqual(first["original_candidate_id"], "C-1")
        self.assertTrue(first["preserve_history"])
        self.assertTrue(first["create_new_attempt"])
        self.assertEqual(first["mode"], "FULL_CURRENT_GOVERNED_LIFECYCLE")
        self.assertEqual(
            first["safety"],
            {
                "live_trading": False,
                "paid_actions": False,
                "wallet_actions": False,
            },
        )
        self.assertEqual(len(list(self.model.revive_root.glob("*.json"))), 2)

    def test_multisession_task_index_only_exposes_active_and_alerts_recent_failures(self):
        now = mod.utc_now()
        write_json(
            self.model.command_state / "T-1.json",
            {
                "task_id": "T-1",
                "route_task_id": "SESSION-A",
                "state": "DISPATCHED",
                "created_at": "2026-10-01T12:00:00Z",
            },
        )
        write_json(
            self.model.executor_state / "T-1.json",
            {
                "task_id": "T-1",
                "status": "PASS",
                "started_at": "2026-10-01T12:00:01Z",
                "finished_at": "2026-10-01T12:00:11Z",
                "exit_code": 0,
            },
        )
        write_json(
            self.model.command_state / "T-2.json",
            {
                "task_id": "T-2",
                "route_task_id": "SESSION-B",
                "state": "DISPATCHED",
                "created_at": now,
            },
        )
        write_json(
            self.model.executor_state / "T-2.json",
            {
                "task_id": "T-2",
                "status": "FAIL",
                "started_at": now,
                "finished_at": now,
                "exit_code": 1,
                "error": "synthetic failure",
            },
        )
        write_json(
            self.model.command_state / "T-3.json",
            {
                "task_id": "T-3",
                "route_task_id": "SESSION-C",
                "state": "DISPATCHED",
                "created_at": now,
            },
        )
        write_json(
            self.model.executor_state / "T-3.json",
            {
                "task_id": "T-3",
                "status": "RUNNING",
                "started_at": now,
                "exit_code": None,
            },
        )
        write_json(
            self.model.command_state / "T-4.json",
            {
                "task_id": "T-4",
                "route_task_id": "SESSION-D",
                "status": "DISPATCHED",
                "claimed_at_utc": "2026-09-01T10:00:00Z",
                "completed_at_utc": "2026-09-01T10:00:01Z",
            },
        )
        snapshot = self.model.build_snapshot(force=True)
        self.assertEqual(snapshot["counts"]["tasks"], 1)
        self.assertEqual(snapshot["counts"]["sessions"], 1)
        self.assertEqual([x["task_id"] for x in snapshot["tasks"]], ["T-3"])
        self.assertNotIn("T-4", {x["task_id"] for x in snapshot["tasks"]})
        self.assertEqual(snapshot["sessions"][0]["route_task_id"], "SESSION-C")
        self.assertEqual(snapshot["task_metrics"]["success"], 1)
        self.assertEqual(snapshot["task_metrics"]["failure"], 1)
        self.assertEqual(snapshot["errors"][0]["task_id"], "T-2")
        self.assertIn("synthetic failure", snapshot["errors"][0]["reason"])
        self.assertEqual(snapshot["chain_alerts"][0]["id"], "T-2")
        self.assertIn("synthetic failure", snapshot["chain_alerts"][0]["reason"])

    def test_git_sync_green_when_production_main_matches_fetched_main(self):
        self.model.mirror_root.mkdir(parents=True)
        (self.model.mirror_root / ".git").mkdir()
        (self.model.mirror_root / ".git/FETCH_HEAD").write_text("dummy", encoding="utf-8")
        same = "a" * 40

        def fake_git(repo, *args):
            key = tuple(args)
            if repo == self.model.repo:
                if key == ("rev-parse", "HEAD"):
                    return same
                if key == ("rev-parse", "refs/heads/main"):
                    return same
                if key == ("branch", "--show-current"):
                    return "main"
                if key == ("status", "--porcelain=v1"):
                    return ""
            if repo == self.model.mirror_root and key == ("rev-parse", "FETCH_HEAD"):
                return same
            return None

        with mock.patch.object(self.model, "_git_output", side_effect=fake_git):
            sync = self.model.git_sync_status()
        self.assertEqual(sync["status"], "GREEN")
        self.assertFalse(sync["dirty"])
        self.assertEqual(sync["production_head"], same)
        self.assertEqual(sync["local_main"], same)
        self.assertEqual(sync["fetched_github_main"], same)

    def test_git_sync_red_on_production_divergence_or_dirty_tree(self):
        self.model.mirror_root.mkdir(parents=True)
        (self.model.mirror_root / ".git").mkdir()
        (self.model.mirror_root / ".git/FETCH_HEAD").write_text("dummy", encoding="utf-8")
        main = "a" * 40
        head = "b" * 40

        def fake_git(repo, *args):
            key = tuple(args)
            if repo == self.model.repo:
                if key == ("rev-parse", "HEAD"):
                    return head
                if key == ("rev-parse", "refs/heads/main"):
                    return main
                if key == ("branch", "--show-current"):
                    return "work"
                if key == ("status", "--porcelain=v1"):
                    return " M control/example.py"
            if repo == self.model.mirror_root and key == ("rev-parse", "FETCH_HEAD"):
                return main
            return None

        with mock.patch.object(self.model, "_git_output", side_effect=fake_git):
            sync = self.model.git_sync_status()
        self.assertEqual(sync["status"], "RED")
        self.assertTrue(sync["dirty"])
        self.assertIn("control/example.py", sync["dirty_paths"])
        self.assertTrue(any("Production HEAD" in x for x in sync["issues"]))
        self.assertTrue(any("niet-vastgelegde" in x for x in sync["issues"]))

    def _seed_proven_chat_route(self):
        write_json(
            self.model.bridge_data / "routes/TASK-ROUTE.json",
            {
                "version": 2,
                "task_id": "TASK-ROUTE",
                "chat_id": "chat-1234",
                "consumer_id": "consumer-old",
            },
        )
        write_json(
            self.model.bridge_data / "sent/event-route.json",
            {
                "event_id": "event-route",
                "task_id": "TASK-ROUTE",
                "message": "delivered",
                "created_at": 1,
            },
        )

    def test_sync_request_routes_to_latest_proven_chat_and_preserves_safety(self):
        self._seed_proven_chat_route()
        red = {
            "status": "RED",
            "production_head": "b" * 40,
            "local_main": "a" * 40,
            "fetched_github_main": "a" * 40,
            "production_branch": "work",
            "dirty": True,
            "dirty_paths": ["control/example.py"],
            "issues": ["Production-worktree bevat niet-vastgelegde wijzigingen."],
        }
        with mock.patch.object(self.model, "git_sync_status", return_value=red):
            result = self.model.request_sync()

        self.assertEqual(result["state"], "QUEUED")
        self.assertFalse(result["deduplicated"])
        self.assertEqual(result["selected_route_task_id"], "TASK-ROUTE")
        self.assertEqual(result["selected_chat_id"], "chat-1234")
        self.assertFalse(result["safety"]["destructive_git"])
        self.assertFalse(result["safety"]["wsl_remote_git_write"])

        route = safe_json(self.model.bridge_data / "routes" / f"{result['trigger_task_id']}.json")
        self.assertEqual(route["chat_id"], "chat-1234")
        self.assertIsNone(route["consumer_id"])

        event = safe_json(self.model.bridge_data / "outbox" / f"{result['event_id']}.json")
        self.assertEqual(event["source"], "prediction_control_center_sync_v1")
        self.assertIn("PREDICTION_CONTROL_SYNC_REQUEST_V1", event["message"])
        self.assertIn("PRODUCTION-RECONCILIATION-20261005", event["message"])
        self.assertIn("Never use reset --hard", event["message"])
        self.assertIn("git_sync.status=GREEN", event["message"])

        request_path = self.model.sync_request_root / f"{result['request_id']}.json"
        self.assertTrue(request_path.is_file())

    def test_sync_request_deduplicates_recent_active_request(self):
        self._seed_proven_chat_route()
        red = {
            "status": "RED",
            "production_head": "b" * 40,
            "local_main": "a" * 40,
            "fetched_github_main": "a" * 40,
            "production_branch": "work",
            "dirty": True,
            "dirty_paths": ["control/example.py"],
            "issues": ["dirty"],
        }
        with mock.patch.object(self.model, "git_sync_status", return_value=red):
            first = self.model.request_sync()
            second = self.model.request_sync()
        self.assertEqual(first["request_id"], second["request_id"])
        self.assertTrue(second["deduplicated"])
        self.assertEqual(len(list((self.model.bridge_data / "outbox").glob("control-sync-*.json"))), 1)

    def test_sync_request_is_noop_when_green(self):
        green = {
            "status": "GREEN",
            "production_head": "a" * 40,
            "local_main": "a" * 40,
            "fetched_github_main": "a" * 40,
            "production_branch": "main",
            "dirty": False,
            "dirty_paths": [],
            "issues": [],
        }
        with mock.patch.object(self.model, "git_sync_status", return_value=green):
            result = self.model.request_sync()
        self.assertEqual(result["state"], "ALREADY_IN_SYNC")
        self.assertFalse(list((self.model.bridge_data / "outbox").glob("*.json")))

    def test_build_log_groups_cross_session_events_into_one_work_item(self):
        projection = self.model.build_log_projection()
        self.assertEqual(projection["counts"]["work_items"], 1)
        self.assertEqual(projection["counts"]["in_progress"], 1)
        self.assertEqual(projection["counts"]["fail_events"], 1)
        item = projection["work_items"][0]
        self.assertEqual(item["work_item_id"], "W-1")
        self.assertEqual(item["status"], "IN_PROGRESS")
        self.assertEqual(item["event_count"], 2)
        self.assertEqual(item["session_routes"], ["SESSION-A", "SESSION-B"])
        self.assertEqual(item["task_ids"], ["TASK-FAIL"])
        self.assertEqual(item["first_incomplete_step"], "Verification.")
        self.assertEqual(item["next_action"], "Continue at the first incomplete step.")

        detail = self.model.work_item_detail("W-1")
        self.assertIsNotNone(detail)
        self.assertEqual(len(detail["timeline"]), 2)
        self.assertEqual(detail["timeline"][0]["outcome"], "PLANNED")
        self.assertEqual(detail["timeline"][1]["outcome"], "FAIL")

    def test_build_log_duplicate_open_objectives_are_flagged(self):
        write_json(
            self.model.repo / "control/build_log/events/20261001T110000Z-W-2.json",
            {
                "schema": "PREDICTION_BUILD_LOG_EVENT_V1",
                "event_id": "20261001T110000Z-W-2",
                "work_item_id": "W-2",
                "created_at_utc": "2026-10-01T11:00:00Z",
                "event_type": "PLAN",
                "work_item_status": "OPEN",
                "outcome": "PLANNED",
                "title": "Duplicate shared work",
                "objective": "Prove one shared objective across sessions.",
                "summary": "Duplicate objective.",
                "why": "Synthetic duplicate.",
                "next_action": "Reuse W-1 instead.",
                "session_route_task_id": "SESSION-C",
                "task_ids": [],
                "commits": [],
                "evidence_refs": [],
                "tags": ["test"],
                "parent_event_id": None,
                "first_incomplete_step": "Do not duplicate.",
            },
        )
        projection = self.model.build_log_projection()
        self.assertEqual(projection["counts"]["duplicate_open_objectives"], 1)
        ids = set(projection["duplicate_open_objectives"][0]["work_item_ids"])
        self.assertEqual(ids, {"W-1", "W-2"})

    def test_lifecycle_status_is_persistent_and_fail_closed(self):
        lifecycle = self.model.lifecycle_status()
        self.assertEqual(lifecycle["full_chain_status"], "NOT_PROVEN")
        self.assertEqual(lifecycle["invariant"], "NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL")

        html = (ROOT / "control/control_center/static/index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('id="persistentLifecycle"'), 1)
        self.assertLess(html.index('id="persistentLifecycle"'), html.index('id="page-home"'))
        self.assertIn("Wat gebeurt er nu? — vaste A→Z-ketenstatus", html)
        self.assertIn("Wat moet nog gebeuren:", html)
        self.assertIn("GERICHT GETEST", html)
        self.assertIn("NOG A→Z BEWIJZEN", html)

    def test_artifact_path_traversal_blocked(self):
        with self.assertRaises(PermissionError):
            self.model.artifact("../secret")

    def test_artifact_read_is_repo_scoped(self):
        result = self.model.artifact("knowledge/runs/R-1.json")
        self.assertEqual(result["path"], "knowledge/runs/R-1.json")
        self.assertIn('"run_id": "R-1"', result["content"])


    def test_owner_ui_is_dutch_but_canonical_codes_remain(self):
        html = (ROOT / "control/control_center/static/index.html").read_text(encoding="utf-8")
        for expected in (
            "Prediction Besturingscentrum",
            "Uitvoeringen",
            "Prestaties",
            "Wacht op onderzoeksdirecteur",
            "Nog geen bewezen voordeel",
            "RUWE BEWIJSGEGEVENS",
            "onderzoeksdashboard • alleen-lezen",
            "Ketenfout direct gemeld",
            "Synchronisatie met main",
            "Geen historisch taakgetal",
            "Alleen wat nu bezig of wachtend is",
            "Wat gebeurt er nu? — vaste A→Z-ketenstatus",
            "Volgende mijlpaal",
            "Wat moet nog gebeuren:",
            "Logboek",
            "Anti-rondjes controle",
            "Bouwlogboek",
            "Open bouwwerk",
            "Sync gestart…",
            "requestSync",
            "/api/sync",
            "fail-closed reconciliatie",
        ):
            self.assertIn(expected, html)
        self.assertIn("NO_PROVEN_EDGE", html)
        self.assertIn("NL_STATUS", html)
        self.assertNotIn(">Control Center<", html)
        self.assertNotIn(">Task performance<", html)
        self.assertNotIn(">RUN DETAIL<", html)
        self.assertNotIn(">RAW EVIDENCE<", html)
        self.assertNotIn("Geen actieve task-state", html)
        self.assertNotIn("research-run.", html)
        self.assertNotIn("failure-state", html)
        self.assertNotIn("runtime-index", html)
        self.assertNotIn("<h3>Director</h3>", html)
        self.assertNotIn("Agents / scouts", html)
        self.assertNotIn("run-artifacts", html)
        self.assertNotIn("Geen gekoppelde artifacts", html)


if __name__ == "__main__":
    unittest.main()
