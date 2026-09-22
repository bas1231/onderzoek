from __future__ import annotations

from pathlib import Path
import importlib.util
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control/hourly/runtime_sync.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_sync_v14_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )
    assert proc.returncode == 0, (args, proc.stdout, proc.stderr)
    return proc.stdout.strip()


def configure(repo: Path) -> None:
    git(repo, "config", "user.name", "runtime-sync-test")
    git(repo, "config", "user.email", "runtime-sync-test@example.invalid")


def seed_repositories(tmp_path: Path) -> tuple[Path, Path, Path]:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    runtime = tmp_path / "runtime"
    updater = tmp_path / "updater"

    remote.mkdir()
    git(remote, "init", "--bare")

    seed.mkdir()
    git(seed, "init", "--initial-branch=main")
    configure(seed)
    (seed / "control").mkdir()
    (seed / "control/app.txt").write_text("v1\n", encoding="utf-8")
    (seed / "knowledge/recon").mkdir(parents=True)
    (seed / "knowledge/recon/watchlist.json").write_text("{\"local\": 0}\n", encoding="utf-8")
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    git(tmp_path, "clone", str(remote), str(runtime))
    git(tmp_path, "clone", str(remote), str(updater))
    configure(runtime)
    configure(updater)
    return remote, runtime, updater


def push_code_update(updater: Path, value: str = "v2\n") -> None:
    (updater / "control/app.txt").write_text(value, encoding="utf-8")
    git(updater, "add", "control/app.txt")
    git(updater, "commit", "-m", "code update")
    git(updater, "push", "origin", "main")


def test_runtime_path_classification_is_narrow():
    mod = load_module()
    assert mod.is_ephemeral("knowledge/runs/recon/hour.json")
    assert mod.is_ephemeral("knowledge/runs/agent_packets/run/scout.json")
    assert mod.is_ephemeral("knowledge/ai_exchange/requests/run.json")
    assert mod.is_ephemeral("knowledge/recon/watchlist.json")
    assert not mod.is_ephemeral("knowledge/candidates/EDGE.json")
    assert not mod.is_ephemeral("hourly-reports/hourly-x.md")
    assert not mod.is_ephemeral("control/hourly/hourly_cycle.py")


def test_dirty_runtime_state_survives_unrelated_fast_forward(tmp_path: Path):
    mod = load_module()
    _, runtime, updater = seed_repositories(tmp_path)
    runtime_state = runtime / "knowledge/runs/recon/hour.json"
    runtime_state.parent.mkdir(parents=True)
    runtime_state.write_text("{\"runtime\": true}\n", encoding="utf-8")
    push_code_update(updater)

    status_path = tmp_path / "status.json"
    result = mod.sync_once(
        runtime,
        status_path=status_path,
        check_writer_services=False,
    )

    assert result["ok"] is True
    assert result["status"] == "UPDATED"
    assert (runtime / "control/app.txt").read_text(encoding="utf-8") == "v2\n"
    assert runtime_state.read_text(encoding="utf-8") == "{\"runtime\": true}\n"
    assert status_path.exists()


def test_durable_dirty_state_blocks_before_update(tmp_path: Path):
    mod = load_module()
    _, runtime, updater = seed_repositories(tmp_path)
    candidate = runtime / "knowledge/candidates/EDGE.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_text("{}\n", encoding="utf-8")
    push_code_update(updater)

    result = mod.sync_once(
        runtime,
        status_path=tmp_path / "status.json",
        check_writer_services=False,
    )

    assert result["ok"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert "knowledge/candidates/EDGE.json" in result["blocked_dirty"]
    assert (runtime / "control/app.txt").read_text(encoding="utf-8") == "v1\n"


def test_incoming_overlap_with_preserved_runtime_state_blocks(tmp_path: Path):
    mod = load_module()
    _, runtime, updater = seed_repositories(tmp_path)
    watch = runtime / "knowledge/recon/watchlist.json"
    watch.write_text("{\"local\": 1}\n", encoding="utf-8")

    remote_watch = updater / "knowledge/recon/watchlist.json"
    remote_watch.write_text("{\"remote\": 1}\n", encoding="utf-8")
    git(updater, "add", "knowledge/recon/watchlist.json")
    git(updater, "commit", "-m", "remote watch update")
    git(updater, "push", "origin", "main")

    result = mod.sync_once(
        runtime,
        status_path=tmp_path / "status.json",
        check_writer_services=False,
    )

    assert result["ok"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert result["overlap_paths"] == ["knowledge/recon/watchlist.json"]
    assert watch.read_text(encoding="utf-8") == "{\"local\": 1}\n"


def test_staged_runtime_state_always_blocks(tmp_path: Path):
    mod = load_module()
    _, runtime, _ = seed_repositories(tmp_path)
    watch = runtime / "knowledge/recon/watchlist.json"
    watch.write_text("{\"local\": 2}\n", encoding="utf-8")
    git(runtime, "add", "knowledge/recon/watchlist.json")

    result = mod.sync_once(
        runtime,
        status_path=tmp_path / "status.json",
        check_writer_services=False,
    )

    assert result["ok"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert result["reason"] == "git index is non-empty"


def test_local_ahead_or_diverged_blocks(tmp_path: Path):
    mod = load_module()
    _, runtime, _ = seed_repositories(tmp_path)
    (runtime / "local.txt").write_text("local commit\n", encoding="utf-8")
    git(runtime, "add", "local.txt")
    git(runtime, "commit", "-m", "local ahead")

    result = mod.sync_once(
        runtime,
        status_path=tmp_path / "status.json",
        check_writer_services=False,
    )

    assert result["ok"] is False
    assert result["status"] == "FAIL_CLOSED"
    assert "ahead of or diverged" in result["reason"]


def test_sync_source_has_no_destructive_git_recovery_commands():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert '"reset"' not in source
    assert '"clean"' not in source
    assert '"stash"' not in source
    assert '"rebase"' not in source
    assert '"--ff-only"' in source


def test_canonical_systemd_service_targets_main_checkout():
    unit = (
        ROOT
        / "control/hourly/systemd/prediction-runtime-sync.service"
    ).read_text(encoding="utf-8")
    assert "WorkingDirectory=%h/prediction_research" in unit
    assert "%h/prediction_research/control/hourly/runtime_sync.py" in unit
    assert "prediction_research_runtime" not in unit
