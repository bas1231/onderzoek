from pathlib import Path
import json
import os
import sys
import tempfile
import time

ROOT = Path.cwd()
LEDGER_DIR = ROOT / "control" / "lifecycle"
LEDGER_DIR.mkdir(parents=True, exist_ok=True)

VALID_STATES = {
    "DISCOVERED",
    "ACCEPTED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "DELIVERED",
    "ACKED",
    "INCIDENT",
}


def record_path(task_id):
    return LEDGER_DIR / f"{task_id}.json"


def load_record(task_id):
    path = record_path(task_id)

    if path.exists():
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    now = time.time()

    return {
        "task_id": task_id,
        "created_at": now,
        "updated_at": now,
        "state": None,
        "history": [],
    }


def write_record(record):
    target = record_path(record["task_id"])

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{record['task_id']}.",
        suffix=".tmp",
        dir=LEDGER_DIR,
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                record,
                handle,
                indent=2,
                sort_keys=True,
            )
            print(file=handle)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_name, target)

    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)

    return record


def update(task_id, state, detail=""):
    if state not in VALID_STATES:
        raise ValueError(
            f"invalid lifecycle state: {state}"
        )

    record = load_record(task_id)
    now = time.time()

    record["state"] = state
    record["updated_at"] = now
    record["history"].append(
        {
            "state": state,
            "at": now,
            "detail": detail,
        }
    )

    return write_record(record)


def self_test():
    task_id = "__LEDGER_SELFTEST__"
    path = record_path(task_id)

    if path.exists():
        path.unlink()

    update(
        task_id,
        "DISCOVERED",
        "self-test",
    )

    record = update(
        task_id,
        "ACCEPTED",
        "self-test",
    )

    result = {
        "status": "ok",
        "final": record["state"],
        "history": len(record["history"]),
        "atomic_file_exists": path.exists(),
    }

    if path.exists():
        path.unlink()

    return result


if __name__ == "__main__":
    if (
        len(sys.argv) == 2
        and sys.argv[1] == "--self-test"
    ):
        print(
            json.dumps(
                self_test(),
                sort_keys=True,
            )
        )

    elif len(sys.argv) >= 3:
        detail = (
            sys.argv[3]
            if len(sys.argv) >= 4
            else ""
        )

        print(
            json.dumps(
                update(
                    sys.argv[1],
                    sys.argv[2],
                    detail,
                ),
                sort_keys=True,
            )
        )

    else:
        print(
            json.dumps(
                {
                    "status": "ready",
                    "ledger_dir": str(
                        LEDGER_DIR.relative_to(ROOT)
                    ),
                },
                sort_keys=True,
            )
        )
