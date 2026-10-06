from __future__ import annotations
import json
from pathlib import Path

root = Path.home() / ".local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4"
task_id = "A2Z-V4-SOL-PROPOSAL-20261006-R2"
result = root / "model_results" / (task_id + ".json")

if not result.is_file() or result.is_symlink():
    print("SOL_R2_RESULT_PRESENT=0")
    raise SystemExit(0)

obj = json.loads(result.read_text(encoding="utf-8"))
print("SOL_R2_RESULT_PRESENT=1")
print("SOL_R2_SCHEMA=" + str(obj.get("schema")))
print("SOL_R2_TASK_ID=" + str(obj.get("task_id")))
print("SOL_R2_PHASE=" + str(obj.get("phase")))
print("SOL_R2_MODEL=" + str(obj.get("model")))
print("SOL_R2_POLICY=" + str(obj.get("model_policy")))
print("SOL_R2_ROUTE=" + str(obj.get("route_task_id")))
print("SOL_R2_CAMPAIGN=" + str(obj.get("campaign_id")))
