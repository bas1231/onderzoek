from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control/hourly/git_checkpoint.py"


def load_module():
    spec = importlib.util.spec_from_file_location("git_checkpoint_v15", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recon_cross_run_state_is_exactly_allowlisted():
    mod = load_module()

    assert mod.matches_allow("knowledge/recon/watchlist.json")
    assert mod.matches_allow("knowledge/recon/opportunity_graph.json")

    # Do not widen the durable publisher to arbitrary Recon output.
    assert not mod.matches_allow("knowledge/recon/debug.json")
    assert not mod.matches_allow("knowledge/recon/raw/source.json")


def test_runtime_only_kwi_checkpoint_is_not_promoted_to_canonical_state():
    mod = load_module()

    assert not mod.matches_allow(
        "knowledge/runs/kwi-full-station-checkpoint-latest.json"
    )
    assert mod.matches_allow("knowledge/runs/twc-revision-summary-latest.json")


def test_existing_sensitive_runtime_prefixes_remain_denied():
    mod = load_module()

    for path in (
        "knowledge/raw/example.json",
        "knowledge/documents/example.json",
        "knowledge/runs/source_sweeps/example.json",
        "knowledge/runs/agent_packets/example.json",
        "knowledge/runs/edge_hunter/example.json",
    ):
        assert mod.denied(path)
