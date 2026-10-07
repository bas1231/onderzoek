from __future__ import annotations

import json
from pathlib import Path

E106 = "control/project_tasks/DEV-PRED-A2Z-POSTBUILD-RETRY-20261006-E106.json"
NEED = {
    "control/codex_supervisor/experiment_gate.py",
    "control/jobs/full_a2z_governed_v4.py",
}


def hydrate(root: Path) -> None:
    spec = json.loads((root / E106).read_text(encoding="utf-8"))
    found = {}
    for op in spec["operations"]:
        path = op.get("path")
        if op.get("type") == "write_text" and path in NEED:
            found[path] = op["content"]
    missing = NEED - set(found)
    if missing:
        raise RuntimeError("E106_SOURCE_MISSING:" + ",".join(sorted(missing)))
    for rel, text in found.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def patch_gate(root: Path) -> None:
    path = root / "control/codex_supervisor/experiment_gate.py"
    text = path.read_text(encoding="utf-8")

    import_old = "import json\nfrom pathlib import Path\n"
    import_new = (
        "import json\nimport sys\nfrom pathlib import Path\n\n"
        "_PROJECT_ROOT = Path(__file__).resolve().parents[2]\n"
        "if str(_PROJECT_ROOT) not in sys.path:\n"
        "    sys.path.insert(0, str(_PROJECT_ROOT))\n"
        "from control.model_execution.direct_sol_chat import worker_policy_error\n"
    )
    if import_old not in text:
        raise RuntimeError("E106_IMPORT_PATTERN_MISSING")
    text = text.replace(import_old, import_new, 1)

    old = '''    if worker.get("model") != slug or worker.get("model_selection", {}).get("policy") != policy or worker.get("model_selection", {}).get("selected_slug") != slug:
        raise ExperimentGateError("EXACT_MODEL_REQUIRED")
    flags = worker.get("command_flags", [])
    if "-m" not in flags or flags[flags.index("-m") + 1] != slug:
        raise ExperimentGateError("MODEL_COMMAND_MISMATCH")
'''
    new = '''    worker_error = worker_policy_error(worker, phase)
    if worker_error:
        raise ExperimentGateError(worker_error)
'''
    if old not in text:
        raise RuntimeError("E106_WORKER_PATTERN_MISSING")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")



def patch_runner(root: Path) -> None:
    path = root / "control/jobs/full_a2z_governed_v4.py"
    text = path.read_text(encoding="utf-8")

    import_old = 'sys.path.insert(0, str(PROJECT / "control/codex_supervisor"))\nimport experiment_gate as gate\nimport model_quality_gate as q\n'
    import_new = (
        'if str(PROJECT) not in sys.path:\n'
        '    sys.path.insert(0, str(PROJECT))\n'
        'sys.path.insert(0, str(PROJECT / "control/codex_supervisor"))\n'
        'from control.model_execution.direct_sol_chat import build_request as build_direct_sol_request\n'
        'import experiment_gate as gate\n'
        'import model_quality_gate as q\n'
    )
    if import_old not in text:
        raise RuntimeError("E106_RUNNER_IMPORT_PATTERN_MISSING")
    text = text.replace(import_old, import_new, 1)

    route_anchor = '''def request(repo, overlay, phase, task_id, prompt):
'''
    route_helper = '''def governed_route(overlay):
    route = str((overlay.get("governed_lifecycle") or {}).get("route_task_id") or "")
    if not route.startswith("SESSION-ROUTE-"):
        raise ValueError("GOVERNED_ROUTE_REQUIRED")
    return route


def request(repo, overlay, phase, task_id, prompt):
'''
    if route_anchor not in text:
        raise RuntimeError("E106_RUNNER_ROUTE_ANCHOR_MISSING")
    text = text.replace(route_anchor, route_helper, 1)

    legacy_request_old = '''def request(repo, overlay, phase, task_id, prompt):
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 100000:
'''
    legacy_request_new = '''def request(repo, overlay, phase, task_id, prompt):
    if phase.startswith("SOL_"):
        raise ValueError("DIRECT_SOL_REQUIRED")
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 100000:
'''
    if legacy_request_old not in text:
        raise RuntimeError("E106_RUNNER_LEGACY_REQUEST_PATTERN_MISSING")
    text = text.replace(legacy_request_old, legacy_request_new, 1)

    request_anchor = '''def prepare_review(repo, overlay, phase, task_id):
'''
    direct_fn = '''def direct_sol_request(repo, overlay, phase, task_id, prompt, binding_sha256):
    if phase not in ("SOL_PROPOSAL", "SOL_BUILD"):
        raise ValueError("DIRECT_SOL_PHASE")
    created = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    route = governed_route(overlay)
    value = build_direct_sol_request(
        task_id=task_id,
        phase=phase,
        campaign_id=CAMPAIGN,
        candidate_id=CID,
        binding_sha256=binding_sha256,
        prompt=prompt,
        delivery_route_task_id=route,
        created_at_utc=created,
    )
    path = repo / "direct_requests" / (task_id + ".json")
    immutable(path, value)
    save(PROJECT / "control/dev_checks/a2z_next_direct_sol_request.json", value)
    print(json.dumps({
        "direct_sol_task_id": task_id,
        "phase": phase,
        "input_sha256": value["input_sha256"],
        "binding_sha256": value["binding_sha256"],
        "request_ref": str(path.relative_to(PROJECT)),
    }, sort_keys=True))


'''
    if request_anchor not in text:
        raise RuntimeError("E106_RUNNER_REVIEW_ANCHOR_MISSING")
    text = text.replace(request_anchor, direct_fn + request_anchor, 1)

    approve_old = '''            request(repo, overlay, "SOL_BUILD", a.next_task, prompt)
'''
    approve_new = '''            direct_sol_request(repo, overlay, "SOL_BUILD", a.next_task, prompt, q.canonical_sha(review))
'''
    if approve_old not in text:
        raise RuntimeError("E106_RUNNER_SOL_BUILD_PATTERN_MISSING")
    text = text.replace(approve_old, approve_new, 1)

    revise_old = '''                request(repo, overlay, "SOL_PROPOSAL", a.next_task,
'''
    revise_new = '''                direct_sol_request(repo, overlay, "SOL_PROPOSAL", a.next_task,
'''
    if revise_old not in text:
        raise RuntimeError("E106_RUNNER_SOL_REVISION_PATTERN_MISSING")
    text = text.replace(revise_old, revise_new, 1)

    revise_tail = '''                        "The revised proposal must return to Astra PREBUILD before any build.\n" + json.dumps({"task_id": a.next_task, "previous_proposal": gate.proposal(repo, overlay), "astra_review": review}, ensure_ascii=False))
'''
    revise_tail_new = '''                        "The revised proposal must return to Astra PREBUILD before any build.\n" + json.dumps({"task_id": a.next_task, "previous_proposal": gate.proposal(repo, overlay), "astra_review": review}, ensure_ascii=False),
                        q.canonical_sha(review))
'''
    if revise_tail not in text:
        raise RuntimeError("E106_RUNNER_SOL_REVISION_TAIL_MISSING")
    text = text.replace(revise_tail, revise_tail_new, 1)

    path.write_text(text, encoding="utf-8")

def main() -> int:
    root = Path.cwd()
    hydrate(root)
    patch_gate(root)
    patch_runner(root)
    print("DIRECT_SOL_E106_GATE_AND_RUNNER_PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
