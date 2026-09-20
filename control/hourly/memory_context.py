from __future__ import annotations

from pathlib import Path
import json
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "knowledge/runs"
MAX_FILE_BYTES = 500_000
MAX_MATCHES = 80
MAX_SNIPPET = 700

CANONICAL_REFS = [
    "AGENTS.md",
    "README.md",
    "PROJECT_IN_EEN_OOGOPSLAG.md",
    "methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md",
    "methodology/RESEARCH_PROTOCOL.md",
    "methodology/EXECUTION_FIRST_DISCOVERY.md",
    "negative_evidence/LEDGER.md",
    "control/TASK_QUEUE.yaml",
    "agents/registry.json",
    "control/hourly/director_manifest.json",
    "control/hourly/research_protocol.json",
]

SEARCH_ROOTS = [
    "candidates/active",
    "knowledge",
    "negative_evidence",
    "experiments",
    "hourly-reports",
]

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt"}


def _safe_text(path: Path) -> str:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _iter_files() -> Iterable[Path]:
    for rel in SEARCH_ROOTS:
        base = ROOT / rel
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            relpath = path.relative_to(ROOT)
            # Raw/source-sweep/run artifacts can be very numerous. The memory
            # layer indexes durable knowledge and recent reports, not raw tapes.
            if "source_sweeps" in relpath.parts or "documents" in relpath.parts:
                continue
            yield path


def _keywords_from_routing(routing: dict) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for role, payload in routing.items():
        if role not in seen:
            words.append(role.replace("_", " "))
            seen.add(role)
        for item in payload.get("evidence", []):
            term = str(item.get("term") or "").strip()
            if len(term) < 3:
                continue
            low = term.lower()
            if low not in seen:
                words.append(term)
                seen.add(low)
    return words[:50]


def _snippet(text: str, pos: int) -> str:
    start = max(0, pos - MAX_SNIPPET // 2)
    stop = min(len(text), pos + MAX_SNIPPET // 2)
    return " ".join(text[start:stop].split())


def _recent_reports(limit: int = 3) -> list[str]:
    base = ROOT / "hourly-reports"
    if not base.exists():
        return []
    return [str(p.relative_to(ROOT)) for p in sorted(base.glob("*.md"))[-limit:]]


def _active_candidates(limit: int = 30) -> list[str]:
    base = ROOT / "candidates/active"
    if not base.exists():
        return []
    return [
        str(p.relative_to(ROOT))
        for p in sorted(base.iterdir())
        if p.is_file()
    ][:limit]


def build(run_id: str) -> tuple[dict, Path]:
    routing_path = RUNS / f"{run_id}-routing.json"
    routing = json.loads(routing_path.read_text()) if routing_path.exists() else {}
    keywords = _keywords_from_routing(routing)

    matches: list[dict] = []
    for path in _iter_files():
        rel = str(path.relative_to(ROOT))
        if rel in CANONICAL_REFS or rel.endswith(f"{run_id}-routing.json"):
            continue
        text = _safe_text(path)
        if not text:
            continue
        lower = text.lower()
        for keyword in keywords:
            pos = lower.find(keyword.lower())
            if pos < 0:
                continue
            matches.append(
                {
                    "ref": rel,
                    "keyword": keyword,
                    "snippet": _snippet(text, pos),
                }
            )
            break
        if len(matches) >= MAX_MATCHES:
            break

    data = {
        "run_id": run_id,
        "purpose": "targeted_git_memory_for_research_director",
        "policy": {
            "git_is_canonical_memory": True,
            "raw_tapes_in_git": False,
            "negative_evidence_must_be_checked": True,
            "duplicate_research_should_be_avoided": True,
            "no_profitability_assumption": True,
        },
        "canonical_refs": [ref for ref in CANONICAL_REFS if (ROOT / ref).exists()],
        "active_candidate_refs": _active_candidates(),
        "recent_hourly_report_refs": _recent_reports(),
        "routing_keywords": keywords,
        "matched_memory": matches,
        "matched_memory_count": len(matches),
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{run_id}-memory-context.json"
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data, out


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    args = parser.parse_args()
    result, path = build(args.run_id)
    print(json.dumps({"ok": True, "matches": result["matched_memory_count"], "path": str(path.relative_to(ROOT))}, sort_keys=True))
