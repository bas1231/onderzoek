from __future__ import annotations

from pathlib import Path
from typing import Any
import json


ROOT = Path(__file__).resolve().parents[2]

TERMINAL_OR_INACTIVE_QUEUE_STATES = {
    "CLOSED_NEGATIVE",
    "PARKED",
}

ROUTABLE_PRIMARY_ROLES = {
    "recon_scout",
    "scout",
    "algebra",
    "settlement",
    "microstructure",
    "behavioral",
    "informed_flow",
    "weather_twc",
}

SEMANTIC_FIELDS = (
    "candidate_id",
    "lane",
    "hypothesis",
    "mechanism",
    "mechanism_scope",
    "open_question",
    "next_decisive_test",
    "required_data",
    "needed_data",
    "required_tests",
    "falsification",
    "blockers",
    "signal_definition",
)

CHECK_FIELDS = (
    "required_clean_room_checks",
    "required_checks",
)

WEATHER_TERMS = (
    "weather",
    "kwi",
    "twc",
    "temperature",
    "station temperature",
    "station observation",
)

SETTLEMENT_TERMS = (
    "settlement",
    "settlement_required",
    "finality",
    "revision",
    "revised",
    "preliminary",
    "resolution source",
    "settlement source",
    "settlement transformation",
    "oracle",
)

ALGEBRA_TERMS = (
    "payoff identity",
    "payout identity",
    "statewise",
    "state-wise",
    "equivalence",
    "equivalent",
    "complete-set",
    "complete set",
    "mutually exclusive",
    "partition",
    "dominance",
    "synthetic portfolio",
)

MICROSTRUCTURE_TERMS = (
    "executable",
    "orderbook",
    "order book",
    "l2",
    "depth",
    "bid/ask",
    "bid ask",
    "maker",
    "taker",
    "fill probability",
    "fills",
    "slippage",
    "hedge cost",
    "hedge latency",
    "latency",
    "spread",
    "rebate",
)

DISCOVERY_TERMS = (
    "discovery",
    "recon",
    "changelog",
    "weak signal",
    "weak-signal",
    "watch triage",
    "watchlist",
    "source discovery",
)

BEHAVIORAL_TERMS = (
    "favorite-longshot",
    "longshot",
    "behavioral",
    "optimism bias",
    "framing",
    "herding",
)

INFORMED_FLOW_TERMS = (
    "informed flow",
    "flow bias",
    "order flow",
    "informed trader",
)


def _flatten(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for key in sorted(value):
            out.extend(_flatten(value[key]))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_flatten(item))
        return out
    return [str(value)]


def _field_text(candidate: dict[str, Any], fields: tuple[str, ...]) -> str:
    parts: list[str] = []
    for field in fields:
        parts.extend(_flatten(candidate.get(field)))
    return " ".join(parts).lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _load_candidate_from_row(
    row: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Load semantic metadata while keeping queue-snapshot fields authoritative."""
    candidate: dict[str, Any] = {}

    inline = row.get("routing_metadata")
    if isinstance(inline, dict):
        candidate.update(inline)

    source_ref = row.get("source_ref")
    if isinstance(source_ref, str) and source_ref:
        candidate_root = (root / "knowledge/candidates").resolve()
        source_path = (root / source_ref).resolve()
        try:
            source_path.relative_to(candidate_root)
            loaded = json.loads(source_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                candidate = loaded
                if isinstance(inline, dict):
                    candidate.update(inline)
        except (OSError, ValueError, json.JSONDecodeError):
            # Queue rows remain usable for explicit inline/test metadata. A
            # missing/unsafe source never broadens routing.
            pass

    # The already-built queue is the eligibility/status snapshot for this run.
    for key in (
        "candidate_id",
        "phase",
        "queue_status",
        "priority",
        "open_question",
        "next_decisive_test",
        "source_ref",
    ):
        if key in row:
            candidate[key] = row[key]

    return candidate


def route_candidate(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic specialist routes derived only from candidate semantics."""
    candidate_id = str(candidate.get("candidate_id") or "")
    status = str(candidate.get("queue_status") or "").upper()
    if not candidate_id or status in TERMINAL_OR_INACTIVE_QUEUE_STATES:
        return []

    lane = str(candidate.get("lane") or "").upper()
    core_text = _field_text(candidate, SEMANTIC_FIELDS)
    check_text = _field_text(candidate, CHECK_FIELDS)

    reasons: dict[str, set[str]] = {}

    def add(role: str, reason: str) -> None:
        if role not in ROUTABLE_PRIMARY_ROLES:
            return
        reasons.setdefault(role, set()).add(reason)

    if lane == "WEATHER":
        add("weather_twc", "lane=WEATHER")
    if lane in {"ALGEBRA", "PAYOFF_ALGEBRA"}:
        add("algebra", f"lane={lane}")
    if lane in {"MICROSTRUCTURE", "EXECUTION"}:
        add("microstructure", f"lane={lane}")
    if lane in {"SETTLEMENT", "MECHANICS"}:
        add("settlement", f"lane={lane}")
    if lane == "BEHAVIORAL":
        add("behavioral", "lane=BEHAVIORAL")
    if lane in {"INFORMED_FLOW", "FLOW"}:
        add("informed_flow", f"lane={lane}")
    if lane in {"DISCOVERY", "RECON"}:
        add("scout", f"lane={lane}")
        add("recon_scout", f"lane={lane}")

    if _contains_any(core_text, WEATHER_TERMS):
        add("weather_twc", "weather/TWC/KWI semantics")

    if _contains_any(core_text + " " + check_text, SETTLEMENT_TERMS):
        add("settlement", "settlement/source/finality/revision semantics")

    if _contains_any(core_text, ALGEBRA_TERMS):
        add("algebra", "statewise payoff/equivalence semantics")

    if _contains_any(core_text, MICROSTRUCTURE_TERMS):
        add("microstructure", "executable market/fill/hedge economics required")

    if _contains_any(core_text, BEHAVIORAL_TERMS):
        add("behavioral", "behavioral mechanism semantics")

    if _contains_any(core_text, INFORMED_FLOW_TERMS):
        add("informed_flow", "informed-flow mechanism semantics")

    # Discovery workers are deliberately opt-in. Merely being DISCOVERED does
    # not route a specialist candidate back to Scout/Recon.
    if _contains_any(core_text, DISCOVERY_TERMS):
        add("scout", "unresolved step is explicit discovery")
        add("recon_scout", "unresolved step is explicit recon/discovery")

    return [
        {
            "candidate_id": candidate_id,
            "role": role,
            "reasons": sorted(role_reasons),
        }
        for role, role_reasons in sorted(reasons.items())
    ]


def hydrate_candidate_routes(
    run_dir: Path,
    candidate_queue: dict[str, Any] | None,
    *,
    root: Path = ROOT,
) -> list[dict[str, Any]]:
    """Attach eligible candidate IDs to relevant primary packets, auditably."""
    if not candidate_queue:
        return []
    rows = candidate_queue.get("queue")
    if not isinstance(rows, list):
        return []

    assignments: list[dict[str, Any]] = []
    ordered_rows = sorted(
        (row for row in rows if isinstance(row, dict)),
        key=lambda row: str(row.get("candidate_id") or ""),
    )

    for row in ordered_rows:
        candidate = _load_candidate_from_row(row, root=root)
        routes = route_candidate(candidate)
        for route in routes:
            role = str(route["role"])
            packet_path = run_dir / f"{role}.json"
            if not packet_path.exists():
                continue

            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            if not isinstance(packet, dict):
                continue

            candidate_id = str(route["candidate_id"])
            ids = {
                str(value)
                for value in packet.get("candidate_ids", [])
                if value
            }
            ids.add(candidate_id)
            packet["candidate_ids"] = sorted(ids)

            audit = packet.get("candidate_routing")
            if not isinstance(audit, list):
                audit = []
            audit = [
                item
                for item in audit
                if not (
                    isinstance(item, dict)
                    and str(item.get("candidate_id")) == candidate_id
                )
            ]
            audit.append({
                "candidate_id": candidate_id,
                "reasons": list(route["reasons"]),
                "phase": candidate.get("phase"),
                "queue_status": candidate.get("queue_status"),
                "source_ref": row.get("source_ref"),
                "open_question": candidate.get("open_question"),
                "next_decisive_test": candidate.get("next_decisive_test"),
            })
            packet["candidate_routing"] = sorted(
                audit,
                key=lambda item: str(item.get("candidate_id") or ""),
            )

            tmp = packet_path.with_suffix(packet_path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(packet, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            tmp.replace(packet_path)

            assignments.append({
                "candidate_id": candidate_id,
                "role": role,
                "reasons": list(route["reasons"]),
                "phase": candidate.get("phase"),
                "queue_status": candidate.get("queue_status"),
            })

    return sorted(
        assignments,
        key=lambda item: (str(item["candidate_id"]), str(item["role"])),
    )
