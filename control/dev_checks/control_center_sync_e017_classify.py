from __future__ import annotations

import io
import unittest

CODES = {
  "test_snapshot_includes_current_and_legacy_ideas": 21,
  "test_candidate_journey_links_runs": 22,
  "test_run_detail_exposes_agent_packets": 23,
  "test_revive_is_immutable_new_request_and_preserves_safety": 24,
  "test_multisession_task_index_only_exposes_active_and_alerts_recent_failures": 25,
  "test_git_sync_green_when_production_main_matches_fetched_main": 26,
  "test_git_sync_red_on_production_divergence_or_dirty_tree": 27,
  "test_sync_request_routes_to_latest_proven_chat_and_preserves_safety": 28,
  "test_sync_request_deduplicates_recent_active_request": 29,
  "test_sync_request_is_noop_when_green": 30,
  "test_build_log_groups_cross_session_events_into_one_work_item": 31,
  "test_build_log_duplicate_open_objectives_are_flagged": 32,
  "test_lifecycle_status_is_persistent_and_fail_closed": 33,
  "test_artifact_path_traversal_blocked": 34,
  "test_artifact_read_is_repo_scoped": 35,
  "test_owner_ui_is_dutch_but_canonical_codes_remain": 36
}

suite = unittest.defaultTestLoader.discover(
    "tests/control_center",
    pattern="test_control_center.py",
)
stream = io.StringIO()
result = unittest.TextTestRunner(
    stream=stream,
    verbosity=2,
    failfast=True,
).run(suite)

if result.wasSuccessful():
    raise SystemExit(0)

issues = list(result.failures) + list(result.errors)
if not issues:
    raise SystemExit(39)
name = issues[0][0].id().split(".")[-1]
raise SystemExit(CODES.get(name, 39))
