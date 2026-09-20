from pathlib import Path
import json
import os
import tempfile
import time

from experiment_cleanup import scan as cleanup_scan

ROOT = Path.cwd()

LEDGER_DIR = ROOT / "control" / "lifecycle"

STATE_ROOT = (
    Path.home()
    / ".local"
    / "state"
    / "prediction-research"
)

INCIDENT_DIR = STATE_ROOT / "incidents"
STATUS_FILE = STATE_ROOT / "supervisor_status.json"

CHECK_INTERVAL = 15

DISCOVERED_LIMIT = 90
ACCEPTED_LIMIT = 90
RESULT_DELIVERY_LIMIT = 90
ACK_LIMIT = 90
RUNNING_GRACE = 20


def now():
    return time.time()


def atomic_json(path, value):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                value,
                handle,
                indent=2,
                sort_keys=True,
            )
            print(file=handle)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp, path)

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_json(path):
    try:
        return json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def task_definition(task_id):
    locations = [
        ROOT / "control/tasks/pending",
        ROOT / "control/tasks/running",
        ROOT / "control/tasks/completed",
        ROOT / "control/tasks/failed",
    ]

    for directory in locations:
        path = directory / f"{task_id}.json"

        if path.exists():
            return load_json(path)

    return None


def incident_path(task_id, reason):
    safe = (
        task_id.replace("/", "_")
        + "__"
        + reason
        + ".json"
    )

    return INCIDENT_DIR / safe


def open_incident(
    task_id,
    reason,
    lifecycle_state,
    age_seconds,
    detail,
):
    path = incident_path(
        task_id,
        reason,
    )

    if path.exists():
        existing = load_json(path)

        if existing:
            existing["last_seen_at"] = now()
            existing["age_seconds"] = round(
                age_seconds,
                1,
            )

            atomic_json(
                path,
                existing,
            )

            return existing

    incident = {
        "incident_id": (
            f"{task_id}:{reason}"
        ),
        "task_id": task_id,
        "reason": reason,
        "lifecycle_state": lifecycle_state,
        "first_seen_at": now(),
        "last_seen_at": now(),
        "age_seconds": round(
            age_seconds,
            1,
        ),
        "detail": detail,
        "status": "OPEN",
        "deliver_to_chat": True,
        "automatic_action": "NONE",
        "running_task_killed": False,
        "paid_action": False,
        "live_trading_action": False,
        "wallet_action": False,
    }

    atomic_json(
        path,
        incident,
    )

    print(
        "INCIDENT",
        task_id,
        reason,
        round(age_seconds, 1),
        flush=True,
    )

    return incident


def inspect_record(path):
    record = load_json(path)

    if not record:
        return []

    task_id = str(
        record.get("task_id")
        or path.stem
    )

    state = record.get("state")
    updated_at = float(
        record.get("updated_at")
        or record.get("created_at")
        or now()
    )

    age = max(
        0,
        now() - updated_at,
    )

    incidents = []

    if (
        state == "DISCOVERED"
        and age > DISCOVERED_LIMIT
    ):
        incidents.append(
            open_incident(
                task_id,
                "NO_ENQUEUE_ACK",
                state,
                age,
                (
                    "Browser ontdekte de taak, maar "
                    "binnen de deadline kwam geen "
                    "duurzame ACCEPTED/enqueue-state."
                ),
            )
        )

    elif (
        state == "ACCEPTED"
        and age > ACCEPTED_LIMIT
    ):
        incidents.append(
            open_incident(
                task_id,
                "EXECUTOR_STALL",
                state,
                age,
                (
                    "Task bleef langer dan "
                    f"{ACCEPTED_LIMIT}s in ACCEPTED."
                ),
            )
        )

    elif state == "RUNNING":
        task = task_definition(task_id) or {}

        timeout = int(
            task.get("timeout_seconds")
            or 60
        )

        limit = (
            timeout
            + RUNNING_GRACE
        )

        if age > limit:
            incidents.append(
                open_incident(
                    task_id,
                    "TASK_RUNTIME_EXCEEDED",
                    state,
                    age,
                    (
                        "Task staat langer in RUNNING "
                        "dan timeout + grace. "
                        "Supervisor beëindigt de "
                        "lopende taak NIET."
                    ),
                )
            )

    elif (
        state in {
            "COMPLETED",
            "FAILED",
        }
        and age > RESULT_DELIVERY_LIMIT
    ):
        incidents.append(
            open_incident(
                task_id,
                "RESULT_DELIVERY_STALL",
                state,
                age,
                (
                    "Resultaat bestaat maar werd "
                    "niet tijdig DELIVERED."
                ),
            )
        )

    elif (
        state == "DELIVERED"
        and age > ACK_LIMIT
    ):
        incidents.append(
            open_incident(
                task_id,
                "CHAT_ACK_STALL",
                state,
                age,
                (
                    "Resultaat werd aangeboden maar "
                    "niet tijdig ACKED."
                ),
            )
        )

    return incidents


def run_once():
    STATE_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    INCIDENT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    records = []

    if LEDGER_DIR.exists():
        records = sorted(
            path
            for path in LEDGER_DIR.glob("*.json")
            if not path.name.startswith(".")
        )

    incidents = []

    for path in records:
        incidents.extend(
            inspect_record(path)
        )

    status = {
        "status": "HEALTHY"
        if not incidents
        else "INCIDENTS_OPEN",
        "checked_at": now(),
        "check_interval_seconds":
            CHECK_INTERVAL,
        "ledger_records":
            len(records),
        "incidents_seen":
            len(incidents),
        "guardrails": {
            "running_task_kill_allowed":
                False,
            "paid_actions_allowed":
                False,
            "live_trading_allowed":
                False,
            "wallet_actions_allowed":
                False,
        },
    }

    # EXPERIMENT_OWNERSHIP_CLEANUP_V1
    # Alleen expliciet toegewezen terminale experimentresources opruimen.
    cleanup_results = cleanup_scan(
        ROOT / "control/experiments",
        dry_run=False,
    )

    status["cleanup"] = {
        "results_seen": len(cleanup_results),
        "cleaned": sum(
            1 for item in cleanup_results
            if item.get("status") == "CLEANED"
        ),
        "already_cleaned": sum(
            1 for item in cleanup_results
            if item.get("status") == "ALREADY_CLEANED"
        ),
    }

    atomic_json(
        STATUS_FILE,
        status,
    )

    return status


def loop():
    print(
        "Prediction Research lifecycle "
        "supervisor started",
        flush=True,
    )

    while True:
        try:
            run_once()

        except Exception as error:
            print(
                "SUPERVISOR_ERROR",
                repr(error),
                flush=True,
            )

        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":
    import sys

    if (
        len(sys.argv) == 2
        and sys.argv[1] == "--once"
    ):
        print(
            json.dumps(
                run_once(),
                sort_keys=True,
            )
        )

    else:
        loop()
