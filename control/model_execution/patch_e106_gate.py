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


def main() -> int:
    root = Path.cwd()
    hydrate(root)
    patch_gate(root)
    print("DIRECT_SOL_E106_GATE_PATCHED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
