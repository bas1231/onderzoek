from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import sys

ROOT = Path.cwd()
PROD = Path.home() / "prediction_research_prod"
FILES = (
    "control/hourly/git_checkpoint.py",
    "control/hourly/runtime_sync.py",
    "control/codex_supervisor/supervisor.py",
    "control/codex_supervisor/candidate_dispatch.py",
    "control/codex_supervisor/build_wake.py",
    "control/tampermonkey_multichat/continuation_manager.py",
    "knowledge/codex_runtime/CONFIG.json",
)

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def production_head() -> str:
    raw = (PROD / ".git/HEAD").read_text(encoding="utf-8").strip()
    if raw.startswith("ref: "):
        ref = raw[5:].strip()
        return (PROD / ".git" / ref).read_text(encoding="utf-8").strip()
    return raw

def has_git_push(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "git":
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == "push":
            return True
    return False

def main() -> int:
    expected = sys.argv[1] if len(sys.argv) > 1 else ""
    assert len(expected) == 40
    assert production_head() == expected
    for rel in FILES:
        assert sha(ROOT / rel) == sha(PROD / rel), rel
    assert not has_git_push(PROD / "control/hourly/git_checkpoint.py")
    assert not has_git_push(PROD / "control/hourly/runtime_sync.py")
    print("PROD_POST_FF_VERIFY=PASS")
    print("PROD_HEAD=" + expected)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
