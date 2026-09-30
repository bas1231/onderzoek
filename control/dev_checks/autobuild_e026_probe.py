from pathlib import Path
import json

prod = Path.home() / "prediction_research_prod"

def excerpt(path: Path, needle: str, before: int, after: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [i for i, line in enumerate(lines) if needle in line]
    if not hits:
        return "NOT_FOUND:" + needle
    i = hits[0]
    lo = max(0, i - before)
    hi = min(len(lines), i + after + 1)
    return "\n".join(f"{n+1}:{lines[n]}" for n in range(lo, hi))

payload = {
    "wiring_test": excerpt(prod / "tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py", "GENERIC-NO-PROTOCOL", 20, 35),
    "candidate_dispatch": excerpt(prod / "control/codex_supervisor/candidate_dispatch.py", "def apply_candidate_result", 5, 75),
}
print("E026_CONTEXT=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
