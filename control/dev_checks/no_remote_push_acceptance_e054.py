from pathlib import Path

ROOT=Path.cwd()
checkpoint=(ROOT/"control/hourly/git_checkpoint.py").read_text(encoding="utf-8")
sync=(ROOT/"control/hourly/runtime_sync.py").read_text(encoding="utf-8")
assert 'git("push"' not in checkpoint
assert "GIT_CHECKPOINT_PUBLISHED" not in checkpoint
assert "LOCAL_ONLY_PENDING_CHATGPT_PUBLICATION" in checkpoint
assert "durable_pending_local" in sync
print("NO_REMOTE_PUSH_ACCEPTANCE=PASS")
