from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "control/hourly/runtime_sync.py"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_sync_v15", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc.stdout.strip()


def commit_file(repo: Path, path: str, text: str, message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    run(repo, "add", "--", path)
    run(repo, "commit", "-m", message)
    return run(repo, "rev-parse", "HEAD")


def make_repos(tmp_path: Path) -> tuple[Path, Path, Path]:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    prod = tmp_path / "prod"

    run(tmp_path, "init", "--bare", str(remote))
    run(tmp_path, "init", "-b", "main", str(seed))
    run(seed, "config", "user.email", "test@example.invalid")
    run(seed, "config", "user.name", "test")
    commit_file(seed, "README.md", "seed\n", "seed")
    run(seed, "remote", "add", "origin", str(remote))
    run(seed, "push", "-u", "origin", "main")
    run(remote, "symbolic-ref", "HEAD", "refs/heads/main")

    run(tmp_path, "clone", str(remote), str(prod))
    run(prod, "config", "user.email", "test@example.invalid")
    run(prod, "config", "user.name", "test")
    return remote, seed, prod


def fake_checkpoint():
    allowed = {
        "knowledge/recon/watchlist.json",
        "knowledge/recon/opportunity_graph.json",
        "knowledge/runs/twc-revision-summary-latest.json",
    }
    return SimpleNamespace(
        denied=lambda path: path.startswith("knowledge/raw/"),
        matches_allow=lambda path: path in allowed,
    )


def configure_module(mod, monkeypatch, prod: Path, tmp_path: Path) -> None:
    monkeypatch.setattr(mod, "ROOT", prod)
    monkeypatch.setattr(mod, "STATUS_PATH", tmp_path / "runtime-sync.json")
    monkeypatch.setattr(mod, "load_module", lambda *_args, **_kwargs: fake_checkpoint())


def test_clean_runtime_fast_forwards_and_preserves_untracked(tmp_path, monkeypatch):
    _remote, seed, prod = make_repos(tmp_path)
    mod = load_module()
    configure_module(mod, monkeypatch, prod, tmp_path)

    (prod / "knowledge/runs").mkdir(parents=True)
    runtime_file = prod / "knowledge/runs/runtime-only.json"
    runtime_file.write_text('{"runtime": true}\n', encoding="utf-8")

    remote_head = commit_file(seed, "docs/new.md", "new\n", "remote update")
    run(seed, "push", "origin", "main")

    result = mod.sync()

    assert result["status"] == "READY"
    assert result["fast_forward"] is True
    assert run(prod, "rev-parse", "HEAD") == remote_head
    assert runtime_file.exists()
    assert result["untracked_file_count"] == 1


def test_unexpected_tracked_code_change_blocks_without_mutation(tmp_path, monkeypatch):
    _remote, seed, prod = make_repos(tmp_path)
    mod = load_module()
    configure_module(mod, monkeypatch, prod, tmp_path)

    local_before = run(prod, "rev-parse", "HEAD")
    (prod / "README.md").write_text("local modification\n", encoding="utf-8")
    commit_file(seed, "docs/remote.md", "remote\n", "remote update")
    run(seed, "push", "origin", "main")

    result = mod.safe_sync()

    assert result["status"] == "BLOCKED"
    assert "unexpected tracked changes" in result["error"]
    assert run(prod, "rev-parse", "HEAD") == local_before
    assert (prod / "README.md").read_text(encoding="utf-8") == "local modification\n"


def test_remote_overlap_with_durable_recon_state_blocks(tmp_path, monkeypatch):
    _remote, seed, prod = make_repos(tmp_path)
    mod = load_module()
    configure_module(mod, monkeypatch, prod, tmp_path)

    rel = "knowledge/recon/watchlist.json"
    seed_head = commit_file(seed, rel, '{"v": 1}\n', "add watchlist")
    run(seed, "push", "origin", "main")
    run(prod, "pull", "--ff-only", "origin", "main")
    assert run(prod, "rev-parse", "HEAD") == seed_head

    (prod / rel).write_text('{"v": "local"}\n', encoding="utf-8")
    commit_file(seed, rel, '{"v": 2}\n', "remote watchlist update")
    run(seed, "push", "origin", "main")
    local_before = run(prod, "rev-parse", "HEAD")

    result = mod.safe_sync()

    assert result["status"] == "BLOCKED"
    assert "overlaps local durable state" in result["error"]
    assert run(prod, "rev-parse", "HEAD") == local_before
    assert (prod / rel).read_text(encoding="utf-8") == '{"v": "local"}\n'


def test_runtime_sync_never_invokes_destructive_git_commands():
    import ast

    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    forbidden = {"reset", "rebase", "stash", "clean"}
    seen = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "git":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            seen.add(first.value)

    assert forbidden.isdisjoint(seen)
