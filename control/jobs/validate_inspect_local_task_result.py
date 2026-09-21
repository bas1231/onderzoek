#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import py_compile
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "control" / "jobs" / "inspect_local_task_result.py"
REAL_TASK = "WEATHER-A19C2-TRANSPORT-RECOVER-026"


def load_module():
    spec = importlib.util.spec_from_file_location("inspect_local_task_result", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError("module load failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


result = {
    "task": "CONTROL-RESULT-INSPECTOR-THREE-CHECK",
    "checks": {},
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
}

# CHECK 1/3 technical
try:
    py_compile.compile(str(TARGET), doraise=True)
    mod = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        d = root / "control" / "results" / "TEST-RESULT-001"
        d.mkdir(parents=True)
        (d / "RESULT.json").write_text(json.dumps({"task_id":"TEST-RESULT-001","status":"completed"}), encoding="utf-8")
        (d / "stdout.log").write_text("hello\n", encoding="utf-8")
        (d / "stderr.log").write_text("", encoding="utf-8")
        out = mod.inspect_task(root, "TEST-RESULT-001")
        ok = out["result"]["status"] == "completed" and out["stdout"] == "hello\n"
    result["checks"]["check_1_technical"] = {"pass": bool(ok)}
except Exception as exc:
    result["checks"]["check_1_technical"] = {"pass": False, "detail": f"{type(exc).__name__}: {exc}"}

# CHECK 2/3 fail-closed
adv = []
try:
    mod = load_module()
    for bad in ("../escape", "/abs", "a", "bad id"):
        try:
            mod.inspect_task(ROOT, bad)
            adv.append({"case": bad, "pass": False})
        except Exception:
            adv.append({"case": bad, "pass": True})
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            mod.inspect_task(root, "MISSING-001")
            adv.append({"case": "missing", "pass": False})
        except FileNotFoundError:
            adv.append({"case": "missing", "pass": True})
        d = root / "control" / "results" / "MISMATCH-001"
        d.mkdir(parents=True)
        (d / "RESULT.json").write_text(json.dumps({"task_id":"OTHER-001"}), encoding="utf-8")
        try:
            mod.inspect_task(root, "MISMATCH-001")
            adv.append({"case": "mismatch", "pass": False})
        except ValueError:
            adv.append({"case": "mismatch", "pass": True})
    result["checks"]["check_2_fail_closed"] = {"pass": all(x["pass"] for x in adv), "cases": adv}
except Exception as exc:
    result["checks"]["check_2_fail_closed"] = {"pass": False, "detail": f"{type(exc).__name__}: {exc}"}

# CHECK 3/3 real local executor result
try:
    mod = load_module()
    out = mod.inspect_task(ROOT, REAL_TASK)
    result["checks"]["check_3_end_to_end"] = {
        "pass": True,
        "task_id": REAL_TASK,
        "result_status": out["result"].get("status"),
        "exit_code": out["result"].get("exit_code"),
        "stdout_present": bool(out.get("stdout")),
        "stderr_present": bool(out.get("stderr")),
    }
except Exception as exc:
    result["checks"]["check_3_end_to_end"] = {
        "pass": False,
        "task_id": REAL_TASK,
        "detail": f"{type(exc).__name__}: {exc}",
    }

checks = result["checks"]
all_pass = all(checks[k].get("pass") is True for k in checks)
result["status"] = "PASS" if all_pass else "BLOCKED"
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all_pass else 1)
