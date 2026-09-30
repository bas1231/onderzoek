from pathlib import Path

ROOT = Path.home() / "prediction_research_prod"
NEEDLE = "NO_PUBLISH_HOOK_UNAVAILABLE"

hits = []
for path in ROOT.rglob("*.py"):
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        continue
    if any(part in {".git", ".venv", "__pycache__"} for part in rel.parts):
        continue
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        continue
    for idx, line in enumerate(lines):
        if NEEDLE not in line:
            continue
        lo = max(0, idx - 10)
        hi = min(len(lines), idx + 11)
        context = " | ".join(f"{n+1}:{lines[n].strip()}" for n in range(lo, hi))
        hits.append(f"FILE={rel.as_posix()} LINE={idx+1} | {context}")

if not hits:
    raise SystemExit("HOOK_LOCATE_FAIL=NO_PUBLISH_HOOK_TEXT_NOT_FOUND")
raise SystemExit("HOOK_LOCATED=" + " || ".join(hits)[:5000])
