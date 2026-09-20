from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import subprocess
import sys

from edge_hunter import prebuild_warrant

ROOT = Path(__file__).resolve().parents[2]
REQUEST_ROOT = ROOT / "experiments/bridge/warrant_requests"
CANDIDATE_DIR = ROOT / "knowledge/candidates"
WARRANT_DIR = ROOT / "knowledge/warrants"
REQUEST_FIELDS = {
    "candidate_id",
    "build_kind",
    "objective",
    "capabilities",
}


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def safe_request_path(value: str, *, root: Path = ROOT) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe request path")

    prefix = "experiments/bridge/warrant_requests/"
    if (
        not relative.as_posix().startswith(prefix)
        or relative.suffix != ".json"
    ):
        raise ValueError(
            "warrant request must be JSON under "
            "experiments/bridge/warrant_requests/"
        )

    resolved = (root / relative).resolve()
    request_root = (root / "experiments/bridge/warrant_requests").resolve()

    if resolved.parent != request_root:
        raise ValueError("warrant request escaped request directory")

    return resolved


def stage_warrant(warrant_path: Path, *, root: Path = ROOT) -> None:
    resolved = warrant_path.resolve()
    warrant_root = (root / "knowledge/warrants").resolve()

    if resolved.parent != warrant_root or resolved.suffix != ".json":
        raise ValueError("warrant path escaped canonical warrant directory")

    relative = resolved.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "add", "--", relative],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("git add warrant failed: " + result.stderr.strip())


def issue_request(
    request_path: Path,
    *,
    root: Path = ROOT,
    stage: bool = True,
) -> dict[str, Any]:
    payload = _load_object(request_path, "warrant request")

    missing = REQUEST_FIELDS - set(payload)
    if missing:
        raise ValueError(
            "missing warrant request fields: " + ",".join(sorted(missing))
        )

    unknown = set(payload) - REQUEST_FIELDS
    if unknown:
        raise ValueError(
            "unknown warrant request fields: " + ",".join(sorted(unknown))
        )

    candidate_id = payload.get("candidate_id")
    if (
        not isinstance(candidate_id, str)
        or not prebuild_warrant.ID_RE.fullmatch(candidate_id)
    ):
        raise ValueError("invalid candidate_id")

    candidate_path = root / "knowledge/candidates" / f"{candidate_id}.json"
    if not candidate_path.exists():
        raise FileNotFoundError("candidate not found")

    candidate = _load_object(candidate_path, "candidate")
    if candidate.get("candidate_id") != candidate_id:
        raise ValueError("candidate_id mismatch")

    policy = _load_object(
        root / "control/edge_hunter/warrant_policy.json",
        "warrant policy",
    )
    build_state = _load_object(
        root / "control/BUILD_STATE.json",
        "build state",
    )

    request = {
        "build_kind": payload.get("build_kind"),
        "objective": payload.get("objective"),
        "capabilities": payload.get("capabilities"),
    }

    evaluated = prebuild_warrant.evaluate(
        candidate,
        request,
        policy=policy,
        build_state=build_state,
    )

    if evaluated["decision"] != "ALLOW_RESEARCH_BUILD":
        return {
            "issued": False,
            "candidate_id": candidate_id,
            "decision": evaluated["decision"],
            "reasons": evaluated["reasons"],
            "warrant_ref": None,
            "decision_sha256": evaluated["decision_sha256"],
        }

    warrant_path = prebuild_warrant.issue(
        candidate,
        request,
        warrant_dir=root / "knowledge/warrants",
        policy=policy,
        build_state=build_state,
    )

    if stage:
        stage_warrant(warrant_path, root=root)

    return {
        "issued": True,
        "candidate_id": candidate_id,
        "decision": evaluated["decision"],
        "reasons": [],
        "warrant_ref": warrant_path.relative_to(root).as_posix(),
        "decision_sha256": evaluated["decision_sha256"],
        "staged_for_executor_commit": bool(stage),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv

    if len(args) != 1:
        print(json.dumps({
            "issued": False,
            "error": "usage: issue_prebuild_warrant.py <request.json>",
        }, sort_keys=True))
        return 2

    try:
        request_path = safe_request_path(args[0])
        result = issue_request(request_path)
    except Exception as exc:
        print(json.dumps({
            "issued": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }, sort_keys=True))
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0 if result["issued"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
