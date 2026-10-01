from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RECEIPTS = Path.home() / ".local/share/prediction-chat-bridge/dev-task-receipts"
OUTPUT = Path("/mnt/c/Users/leonh/Prediction-Results")
TASK_RE = re.compile(r"^DEV-PRED-[A-Za-z0-9._:-]{1,150}$")
KV_RE = re.compile(r"^([A-Z][A-Z0-9_]{1,120})=(.*)$")
SAFE_VALUES = {"PASS", "FAIL", "FINISHED", "NOT_ACTIVATED_PRE_REVIEW", "UNPROVEN", "NO_PROVEN_EDGE", "ACTIVE", "INACTIVE"}


def parse_receipt(path: Path):
    raw = path.read_bytes()
    lines = raw.decode("utf-8", errors="replace").splitlines()
    fields = {}
    markers = []
    for line in lines:
        match = KV_RE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        fields.setdefault(key, value)
        if value in SAFE_VALUES or key.endswith("_STATUS") or value in {"PASS", "FAIL"}:
            item = f"{key}={value}"
            if item not in markers:
                markers.append(item)
    task_id = fields.get("TASK_ID") or fields.get("DEV_TASK_ID")
    if not task_id or not TASK_RE.fullmatch(task_id) or fields.get("STATUS") != "FINISHED":
        return None
    try:
        exit_code = int(fields.get("EXIT_CODE")) if fields.get("EXIT_CODE") is not None else None
    except ValueError:
        exit_code = None
    return {
        "schema": "PREDICTION_DRIVE_RESULT_V1",
        "task_id": task_id,
        "status": fields.get("STATUS"),
        "exit_code": exit_code,
        "project_task_status": fields.get("PROJECT_TASK_STATUS"),
        "dev_task_status": fields.get("DEV_TASK_STATUS"),
        "error_class": fields.get("ERROR_CLASS"),
        "assertions": markers[:200],
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "receipt_completed_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_receipt": path.name,
        "safety": {
            "full_receipt_exported": False,
            "prediction_tasks_only": True,
            "credentials_exported": False,
        },
    }


def atomic_json(path: Path, obj) -> None:
    data = (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def export_receipt(path: Path, output_dir: Path = OUTPUT) -> str:
    obj = parse_receipt(path)
    if obj is None:
        return "SKIP"
    target = output_dir / f"{obj['task_id']}.json"
    if target.exists():
        try:
            previous = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            previous = {}
        if previous.get("receipt_sha256") == obj["receipt_sha256"]:
            return "UNCHANGED"
        conflict = output_dir / f"{obj['task_id']}.conflict.{obj['receipt_sha256'][:12]}.json"
        if not conflict.exists():
            atomic_json(conflict, obj)
        return "CONFLICT"
    atomic_json(target, obj)
    return "EXPORTED"


def scan(receipt_dir: Path = RECEIPTS, output_dir: Path = OUTPUT) -> int:
    if not receipt_dir.is_dir():
        print("RESULT_EXPORTER_RECEIPT_DIR_MISSING")
        return 2
    if not output_dir.is_dir():
        print("RESULT_EXPORTER_OUTPUT_DIR_MISSING")
        return 3
    counts = {"EXPORTED": 0, "UNCHANGED": 0, "SKIP": 0, "CONFLICT": 0}
    for path in sorted(receipt_dir.glob("DEV-PRED-*.log")):
        result = export_receipt(path, output_dir)
        counts[result] += 1
        print(f"RESULT_EXPORT {path.name} {result}")
    print("PREDICTION_DRIVE_RESULT_EXPORTER=PASS")
    for key in sorted(counts):
        print(f"RESULT_EXPORT_{key}={counts[key]}")
    return 4 if counts["CONFLICT"] else 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        out = root / "out"
        out.mkdir()
        receipt = root / "DEV-PRED-SELFTEST-E001.log"
        receipt.write_text("TASK_ID=DEV-PRED-SELFTEST-E001\nEXIT_CODE=0\nSTATUS=FINISHED\nPROJECT_TASK_STATUS=PASS\nSELFTEST_ASSERTION=PASS\nDEV_TASK_STATUS=PASS\n", encoding="utf-8")
        obj = parse_receipt(receipt)
        assert obj and obj["exit_code"] == 0 and obj["project_task_status"] == "PASS"
        assert "SELFTEST_ASSERTION=PASS" in obj["assertions"]
        assert export_receipt(receipt, out) == "EXPORTED"
        assert export_receipt(receipt, out) == "UNCHANGED"
        original = (out / "DEV-PRED-SELFTEST-E001.json").read_bytes()
        receipt.write_text("TASK_ID=DEV-PRED-SELFTEST-E001\nEXIT_CODE=2\nSTATUS=FINISHED\nPROJECT_TASK_STATUS=FAIL\n", encoding="utf-8")
        assert export_receipt(receipt, out) == "CONFLICT"
        assert (out / "DEV-PRED-SELFTEST-E001.json").read_bytes() == original
    print("RESULT_EXPORTER_SELFTEST=PASS")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    raise SystemExit(selftest() if args.selftest else scan() if args.scan else 64)
