#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path.cwd().resolve()
RESULTS = ROOT / "control" / "results"
EVIDENCE = ROOT / "evidence" / "weather"
TASK_RE = re.compile(r"^[A-Za-z0-9._-]{3,160}$")


def emit(obj: dict, code: int = 0) -> None:
    obj.setdefault("live_trading", False)
    obj.setdefault("paid_action", False)
    obj.setdefault("wallet_action", False)
    obj.setdefault("economic_conclusion", "NO_PROVEN_EDGE")
    print(json.dumps(obj, indent=2, sort_keys=True))
    raise SystemExit(code)


def read_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, dict):
        return None, "JSON_NOT_OBJECT"
    return value, None


def safe_children(base: Path, task_id: str) -> list[Path]:
    task_dir = (base / task_id).resolve()
    if task_dir.parent != base.resolve():
        return []
    if not task_dir.is_dir():
        return []
    return sorted(p for p in task_dir.rglob("*") if p.is_file())


def main() -> None:
    if len(sys.argv) != 2:
        emit({
            "status": "BLOCKED",
            "checks": {
                "check_1_technical": {"pass": True, "detail": "script loaded"},
                "check_2_fail_closed": {"pass": True, "detail": "argument count rejected"},
                "check_3_end_to_end": {"pass": False, "detail": "task id missing"},
            },
            "next_gate": "SUPPLY_TASK_ID",
        }, 2)

    task_id = sys.argv[1]
    check1 = {"pass": True, "detail": "script loaded and root resolved", "root": str(ROOT)}

    safe_id = bool(TASK_RE.fullmatch(task_id))
    if not safe_id:
        emit({
            "status": "BLOCKED",
            "task_id": task_id,
            "checks": {
                "check_1_technical": check1,
                "check_2_fail_closed": {"pass": True, "detail": "unsafe task id rejected"},
                "check_3_end_to_end": {"pass": False, "detail": "not attempted"},
            },
            "next_gate": "INVALID_TASK_ID",
        }, 3)

    files = safe_children(RESULTS, task_id)
    result_path = (RESULTS / task_id / "RESULT.json").resolve()
    safe_path = result_path.parent.parent == RESULTS.resolve()
    check2 = {
        "pass": bool(safe_path),
        "detail": "task result path constrained under control/results",
        "result_path": str(result_path),
    }
    if not safe_path:
        emit({
            "status": "BLOCKED",
            "task_id": task_id,
            "checks": {
                "check_1_technical": check1,
                "check_2_fail_closed": check2,
                "check_3_end_to_end": {"pass": False, "detail": "not attempted"},
            },
            "next_gate": "UNSAFE_RESULT_PATH",
        }, 4)

    result, result_error = read_json(result_path) if result_path.is_file() else (None, "RESULT_JSON_MISSING")

    text_artifacts: dict[str, str] = {}
    for p in files:
        if p == result_path:
            continue
        if p.stat().st_size > 200_000:
            continue
        try:
            text_artifacts[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8", errors="replace")[-20000:]
        except Exception:
            pass

    evidence_matches: dict[str, object] = {}
    if EVIDENCE.is_dir():
        for p in sorted(EVIDENCE.glob("*")):
            name = p.name.upper()
            if not p.is_file() or not any(token in name for token in ("A19C", "CLOCK", "A19B")):
                continue
            if p.stat().st_size > 500_000:
                continue
            try:
                if p.suffix.lower() == ".json":
                    obj, err = read_json(p)
                    evidence_matches[str(p.relative_to(ROOT))] = obj if obj is not None else {"parse_error": err}
                else:
                    evidence_matches[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8", errors="replace")[-20000:]
            except Exception as exc:
                evidence_matches[str(p.relative_to(ROOT))] = {"read_error": f"{type(exc).__name__}: {exc}"}

    check3_pass = result is not None
    next_gate = "DIAGNOSE_FROM_LOCAL_RESULT" if check3_pass else "LOCAL_RESULT_NOT_AVAILABLE"

    emit({
        "status": "PASS" if check3_pass else "BLOCKED",
        "task_id": task_id,
        "checks": {
            "check_1_technical": check1,
            "check_2_fail_closed": check2,
            "check_3_end_to_end": {
                "pass": check3_pass,
                "result_error": result_error,
                "task_artifact_count": len(files),
                "weather_evidence_count": len(evidence_matches),
            },
        },
        "result": result,
        "task_text_artifacts": text_artifacts,
        "weather_evidence": evidence_matches,
        "next_gate": next_gate,
    }, 0 if check3_pass else 5)


if __name__ == "__main__":
    main()
