from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control/hourly/git_checkpoint.py"


def load_module():
    spec = importlib.util.spec_from_file_location("git_checkpoint_v15", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def make_repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    run_git(repo, "config", "user.name", "Checkpoint Test")
    run_git(repo, "config", "user.email", "checkpoint@example.invalid")

    (repo / "notes.txt").write_text("base\n", encoding="utf-8")
    run_git(repo, "add", "notes.txt")
    run_git(repo, "commit", "-m", "initial")
    run_git(repo, "remote", "add", "origin", str(remote))
    run_git(repo, "push", "-u", "origin", "main")
    return repo, remote


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


def test_checkpoint_preserves_unrelated_preexisting_staged_state(tmp_path):
    repo, remote = make_repo(tmp_path)
    mod = load_module()
    mod.ROOT = repo
    mod.STATUS_PATH = tmp_path / "state.json"

    # Simulate a different local process/session with intentional staged work.
    (repo / "notes.txt").write_text("staged-local-work\n", encoding="utf-8")
    run_git(repo, "add", "notes.txt")
    staged_patch_before = run_git(repo, "diff", "--cached", "--binary").stdout

    report = repo / "hourly-reports/hourly-20260924T080000+0200.md"
    report.parent.mkdir(parents=True)
    report.write_text("# durable hourly report\n", encoding="utf-8")

    assert mod.main() == 0

    # The unrelated staged patch must survive byte-for-byte.
    assert run_git(repo, "diff", "--cached", "--binary").stdout == staged_patch_before
    assert run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines() == [
        "notes.txt"
    ]

    assert (
        run_git(repo, "show", "HEAD:hourly-reports/hourly-20260924T080000+0200.md")
        .stdout
        == "# durable hourly report\n"
    )
    assert subprocess.run(
        [
            "git",
            f"--git-dir={remote}",
            "show",
            "main:hourly-reports/hourly-20260924T080000+0200.md",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout == "# durable hourly report\n"

    state = json.loads(mod.STATUS_PATH.read_text(encoding="utf-8"))
    assert state["status"] == "PUBLISHED"
    assert state["preserved_staged_count"] == 1


def test_checkpoint_fails_closed_on_preexisting_staged_candidate(tmp_path):
    repo, _remote = make_repo(tmp_path)
    mod = load_module()
    mod.ROOT = repo
    mod.STATUS_PATH = tmp_path / "state.json"

    report = repo / "hourly-reports/hourly-20260924T080000+0200.md"
    report.parent.mkdir(parents=True)
    report.write_text("# intentionally staged elsewhere\n", encoding="utf-8")
    run_git(repo, "add", "hourly-reports/hourly-20260924T080000+0200.md")

    head_before = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    patch_before = run_git(repo, "diff", "--cached", "--binary").stdout

    assert mod.main() == 1
    assert run_git(repo, "rev-parse", "HEAD").stdout.strip() == head_before
    assert run_git(repo, "diff", "--cached", "--binary").stdout == patch_before

    state = json.loads(mod.STATUS_PATH.read_text(encoding="utf-8"))
    assert state["status"] == "FAIL_CLOSED"
    assert "already staged" in state["reason"]
