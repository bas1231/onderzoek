from __future__ import annotations

from pathlib import Path
from typing import Any
import importlib.util
import json
import sys


ROOT = Path(__file__).resolve().parents[2]


def _load_architecture():
    path = ROOT / "control/hourly/research_os_architecture.py"
    spec = importlib.util.spec_from_file_location("research_os_architecture_e007", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ARCH = _load_architecture()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _priority_index(bucket: str) -> int:
    try:
        return ARCH.SCHEDULER_PRIORITY.index(bucket)
    except ValueError:
        return len(ARCH.SCHEDULER_PRIORITY)


def _shape_dict(shape: Any) -> dict[str, Any]:
    return {
        "name": shape.name,
        "max_parallel_workers": shape.max_parallel_workers,
        "dependencies": shape.dependencies,
        "uncertainty": shape.uncertainty,
        "time_sensitivity": shape.time_sensitivity,
        "novelty": shape.novelty,
        "expected_decision_value": shape.expected_decision_value,
    }


def schedule(run_dir: Path) -> dict[str, Any]:
    """Schedule the five permanent specialist domains plus isolated reproducer.

    Research Director is coordination, not a specialist slot. The transient
    Independent Reproducer is scheduled separately and never displaces one of
    the five permanent research domains; when present it remains LOW_SEQUENTIAL
    and isolated from originating conclusions.
    """
    packets: list[dict[str, Any]] = []
    paths: dict[str, Path] = {}
    for path in sorted(run_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        packet = load_json(path)
        role = str(packet.get("agent_id") or "")
        packets.append(packet)
        paths[role] = path

    permanent_eligible = []
    transient_eligible = []
    for packet in packets:
        role = str(packet.get("agent_id") or "")
        if role == "research_director" or packet.get("status") not in {"READY", "RESULT_READY"}:
            continue
        shape = ARCH.classify_task_shape(packet)
        bucket = ARCH.scheduler_bucket(packet)
        row = (
            _priority_index(bucket),
            role,
            packet,
            shape,
            bucket,
        )
        if role == "independent_reproducer":
            transient_eligible.append(row)
        elif role in set(ARCH.DYNAMIC_WORKERS):
            permanent_eligible.append(row)

    permanent_eligible.sort(key=lambda item: (item[0], item[1]))
    transient_eligible.sort(key=lambda item: (item[0], item[1]))
    selected = permanent_eligible[:5]
    selected_roles = {item[1] for item in selected}

    schedule_rows = []
    for _, role, packet, shape, bucket in permanent_eligible:
        scheduled = role in selected_roles
        updated = dict(packet)
        updated["task_shape"] = _shape_dict(shape)
        updated["scheduler_priority"] = bucket
        updated["dynamic_worker_scheduled"] = scheduled
        updated["isolated_validation_worker"] = False
        if not scheduled and updated.get("status") == "READY":
            updated["status"] = "PENDING"
            updated["orchestrator_reason"] = "deferred_by_dynamic_worker_pool"
        save_json(paths[role], updated)
        schedule_rows.append({
            "agent_id": role,
            "scheduled": scheduled,
            "isolated": False,
            "scheduler_priority": bucket,
            "task_shape": updated["task_shape"],
            "candidate_ids": updated.get("candidate_ids", []),
        })

    transient_roles = []
    for _, role, packet, shape, bucket in transient_eligible:
        updated = dict(packet)
        updated["task_shape"] = _shape_dict(shape)
        updated["scheduler_priority"] = bucket
        updated["dynamic_worker_scheduled"] = True
        updated["isolated_validation_worker"] = True
        updated["blind"] = True
        save_json(paths[role], updated)
        transient_roles.append(role)
        schedule_rows.append({
            "agent_id": role,
            "scheduled": True,
            "isolated": True,
            "scheduler_priority": bucket,
            "task_shape": updated["task_shape"],
            "candidate_ids": updated.get("candidate_ids", []),
        })

    result = {
        "schema": "PVA_TASK_SHAPE_SCHEDULE_V1",
        "run_id": run_dir.name,
        "permanent_agents": list(ARCH.PERMANENT_AGENTS),
        "dynamic_worker_capacity": 5,
        "scheduled_dynamic_workers": [item[1] for item in selected],
        "scheduled_transient_workers": transient_roles,
        "protected_discovery_lanes": list(ARCH.PROTECTED_DISCOVERY_LANES),
        "priority_order": list(ARCH.SCHEDULER_PRIORITY),
        "tasks": schedule_rows,
        "guardrails": {
            "live_trading": False,
            "paid_actions": False,
            "wallet_actions": False,
            "openai_api": False,
        },
    }
    save_json(run_dir / "_task_schedule.json", result)
    return result
