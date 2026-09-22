#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

MAIN = Path.home() / "prediction_research"
WEATHER = Path.home() / "prediction_research_weather"
TOKENS = ("a19c", "a19c2", "recover", "clock", "a19b_v2")


def run(cwd: Path, *args: str, timeout: int = 20) -> dict:
    try:
        cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout[-12000:],
            "stderr": cp.stderr[-6000:],
        }
    except Exception as exc:
        return {
            "returncode": 255,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {"_type": type(obj).__name__}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def interesting_files(root: Path) -> list[str]:
    found: list[str] = []
    for rel_root in ("control/jobs", "control/weather", "evidence/weather", "control/results"):
        base = root / rel_root
        if not base.exists():
            continue
        try:
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(root).as_posix()
                low = rel.lower()
                if any(token in low for token in TOKENS):
                    found.append(rel)
                    if len(found) >= 250:
                        return sorted(found)
        except Exception:
            continue
    return sorted(found)


def evidence_summaries(root: Path, files: list[str]) -> dict:
    out: dict[str, object] = {}
    priority = {
        "evidence/weather/WEATHER-AWAY-A19B-latest.json",
        "control/results/WEATHER-A19C2-RECOVER-031/RESULT.json",
    }
    candidates = set(priority)
    for rel in files:
        low = rel.lower()
        if rel.endswith(".json") and any(token in low for token in ("a19c", "recover", "a19b_v2", "clock")):
            candidates.add(rel)
    for rel in sorted(candidates):
        path = root / rel
        if not path.is_file():
            out[rel] = {"exists": False}
            continue
        obj = read_json(path)
        summary = {
            "exists": True,
            "status": obj.get("status"),
            "next_gate": obj.get("next_gate"),
            "exit_code": obj.get("exit_code"),
            "task_id": obj.get("task_id") or obj.get("task"),
            "economic_conclusion": obj.get("economic_conclusion"),
        }
        if "result" in obj and isinstance(obj["result"], dict):
            summary["result_status"] = obj["result"].get("status")
            summary["result_exit_code"] = obj["result"].get("exit_code")
        if "checks" in obj:
            summary["checks"] = obj.get("checks")
        if "steps" in obj:
            steps = obj.get("steps") or {}
            if isinstance(steps, dict):
                summary["step_keys"] = sorted(steps.keys())
                for key, val in steps.items():
                    if isinstance(val, dict):
                        summary[f"step:{key}"] = {
                            "status": val.get("status"),
                            "returncode": val.get("returncode"),
                            "next_gate": val.get("next_gate"),
                        }
        if "_error" in obj:
            summary["parse_error"] = obj["_error"]
        out[rel] = summary
    return out


result: dict[str, object] = {
    "task": "WEATHER-A19C2-RECOVERY-DIAGNOSTIC",
    "status": "DIAGNOSTIC_ONLY",
    "economic_conclusion": "NO_PROVEN_EDGE",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "openai_api": False,
}

for label, root in (("main", MAIN), ("weather", WEATHER)):
    section: dict[str, object] = {"root": str(root), "exists": root.is_dir()}
    if root.is_dir():
        section["branch"] = run(root, "git", "branch", "--show-current")
        section["head"] = run(root, "git", "rev-parse", "HEAD")
        section["tracked_status"] = run(root, "git", "status", "--porcelain", "--untracked-files=no")
        section["log_relevant"] = run(
            root,
            "git", "log", "--oneline", "-40", "--regexp-ignore-case",
            "--grep=A19C", "--grep=RECOVER", "--grep=CLOCK", "--grep=A19B.V2"
        )
        files = interesting_files(root)
        section["interesting_files"] = files
        section["evidence"] = evidence_summaries(root, files)
        section["v2_validator_exists"] = (root / "control/jobs/validate_madis_ldm_a19b_v2.py").is_file()
    result[label] = section

local_result = MAIN / "control/results/WEATHER-A19C2-RECOVER-031/RESULT.json"
result["recover_031_local_result"] = (
    read_json(local_result) if local_result.is_file() else {"exists": False}
)

print(json.dumps(result, indent=2, sort_keys=True))
