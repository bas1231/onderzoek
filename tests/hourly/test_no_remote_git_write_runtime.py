from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]

def git_calls(path: Path):
    tree=ast.parse(path.read_text(encoding="utf-8"))
    out=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call): continue
        if not isinstance(node.func,ast.Name) or node.func.id!="git": continue
        if not node.args: continue
        first=node.args[0]
        if isinstance(first,ast.Constant) and isinstance(first.value,str):
            out.append(first.value)
    return out

def test_checkpoint_runtime_never_pushes_remote():
    calls=git_calls(ROOT/"control/hourly/git_checkpoint.py")
    assert "push" not in calls

def test_runtime_sync_never_pushes_remote():
    calls=git_calls(ROOT/"control/hourly/runtime_sync.py")
    assert "push" not in calls

def test_checkpoint_records_local_pending_handoff():
    text=(ROOT/"control/hourly/git_checkpoint.py").read_text(encoding="utf-8")
    assert "LOCAL_ONLY_PENDING_CHATGPT_PUBLICATION" in text
    assert "GIT_CHECKPOINT_LOCAL_ONLY_PENDING" in text

def test_runtime_sync_preserves_local_pending_state():
    text=(ROOT/"control/hourly/runtime_sync.py").read_text(encoding="utf-8")
    assert "durable_pending_local" in text
    assert "unexpected tracked changes remain after sync" in text
