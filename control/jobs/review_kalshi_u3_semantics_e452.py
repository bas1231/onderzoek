from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INFILE = ROOT / "knowledge" / "research" / "kalshi_u3_semantics_e451.json"
GRID_NOTE = ROOT / "knowledge" / "research" / "KALSHI-U3-BLS-GRID-EVIDENCE-20260922.md"
OUTFILE = ROOT / "knowledge" / "research" / "kalshi_u3_semantics_e452_review.json"

EXPECTED = {
    "KXU3-26SEP-T4.0": ("threshold", 4.0),
    "KXU3-26SEP-T4.1": ("threshold", 4.1),
    "KXECONSTATU3-26SEP-T4.1": ("exact", 4.1),
}


def _text(semantic: dict[str, Any]) -> str:
    parts = []
    for key in (
        "title",
        "subtitle",
        "yes_sub_title",
        "no_sub_title",
        "rules_primary",
        "rules_secondary",
    ):
        value = semantic.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts).lower()


def _status(ok: bool, detail: str) -> dict[str, str]:
    return {"status": "PASS" if ok else "FAIL", "detail": detail}


def _unknown(detail: str) -> dict[str, str]:
    return {"status": "UNKNOWN", "detail": detail}


def _relation_check(kind: str, strike: float, text: str) -> dict[str, str]:
    strike_text = re.escape(f"{strike:.1f}")
    if kind == "threshold":
        ok = bool(re.search(rf"above\s+{strike_text}\s*%?", text))
        return _status(ok, f"expected explicit above {strike:.1f}% semantics")
    ok = bool(
        re.search(rf"exactly\s+{strike_text}\s*%?", text)
        or re.search(rf"(?:is|equals?)\s+{strike_text}\s*%?", text)
    )
    return _status(ok, f"expected explicit equality/exactly {strike:.1f}% semantics")


def _common_source_checks(text: str) -> dict[str, dict[str, str]]:
    return {
        "u3_statistic": _status(
            ("u-3" in text or "u3" in text) and "unemployment" in text,
            "must identify U-3 unemployment statistic",
        ),
        "bls_source": _status(
            "bureau of labor statistics" in text or re.search(r"\bbls\b", text) is not None,
            "must identify Bureau of Labor Statistics",
        ),
        "employment_situation": _status(
            "employment situation" in text,
            "must identify Employment Situation report",
        ),
        "reference_month": _status(
            "september" in text and "2026" in text,
            "must identify September 2026",
        ),
    }


def _same_nonempty(rows: list[dict[str, Any]], key: str) -> dict[str, str]:
    values = [row.get(key) for row in rows]
    if any(value in (None, "") for value in values):
        return _unknown(f"{key} absent/empty on at least one market")
    return _status(len({json.dumps(v, sort_keys=True) for v in values}) == 1, f"{key} must match across all markets")


def _policy_presence(rows: list[dict[str, Any]], terms: tuple[str, ...], label: str) -> dict[str, str]:
    combined = " ".join(_text(row) for row in rows)
    if any(term in combined for term in terms):
        return {"status": "SUPPORTED", "detail": f"explicit {label} language found; manual alignment review still required"}
    return _unknown(f"no explicit {label} language captured in market rules")


def review_artifact(artifact: dict[str, Any], *, grid_note_present: bool) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    checks["semantic_only_capture"] = _status(
        artifact.get("price_fields_captured") is False
        and artifact.get("order_book_captured") is False,
        "capture must contain no price/order-book data",
    )

    tickers = artifact.get("tickers")
    if not isinstance(tickers, dict):
        tickers = {}
    checks["ticker_universe"] = _status(
        set(tickers) == set(EXPECTED),
        "artifact must contain exactly the three preregistered tickers",
    )

    semantic_rows: list[dict[str, Any]] = []
    per_market: dict[str, Any] = {}
    for ticker, (kind, strike) in EXPECTED.items():
        row = tickers.get(ticker)
        semantic = row.get("semantic") if isinstance(row, dict) else None
        if not isinstance(semantic, dict):
            per_market[ticker] = {"artifact": _status(False, "missing semantic object")}
            continue

        semantic_rows.append(semantic)
        text = _text(semantic)
        market_checks = {
            "ticker_matches": _status(semantic.get("ticker") == ticker, "ticker must match requested market"),
            "relation": _relation_check(kind, strike, text),
            **_common_source_checks(text),
        }
        per_market[ticker] = market_checks

    checks["markets"] = per_market

    if len(semantic_rows) == len(EXPECTED):
        checks["close_time_alignment"] = _same_nonempty(semantic_rows, "close_time")
        checks["latest_expiration_alignment"] = _same_nonempty(semantic_rows, "latest_expiration_time")
        checks["settlement_timer_alignment"] = _same_nonempty(semantic_rows, "settlement_timer_seconds")

        early_values = [row.get("can_close_early") for row in semantic_rows]
        if all(value is False for value in early_values):
            checks["early_close_alignment"] = {"status": "PASS", "detail": "all markets explicitly cannot close early"}
        elif any(value is None for value in early_values):
            checks["early_close_alignment"] = _unknown("can_close_early missing on at least one market")
        elif len(set(early_values)) != 1:
            checks["early_close_alignment"] = _status(False, "can_close_early differs across markets")
        else:
            checks["early_close_alignment"] = _same_nonempty(semantic_rows, "early_close_condition")

        checks["revision_policy"] = _policy_presence(
            semantic_rows,
            ("revision", "revised", "first reported", "initial release", "subsequent revision"),
            "revision/first-release policy",
        )
        checks["missing_release_policy"] = _policy_presence(
            semantic_rows,
            ("not released", "no release", "delayed", "delay", "cancelled", "canceled", "unavailable", "missing data"),
            "missing/delayed/cancelled-release policy",
        )
        checks["secondary_rule_alignment"] = _same_nonempty(semantic_rows, "rules_secondary")
    else:
        for key in (
            "close_time_alignment",
            "latest_expiration_alignment",
            "settlement_timer_alignment",
            "early_close_alignment",
            "revision_policy",
            "missing_release_policy",
            "secondary_rule_alignment",
        ):
            checks[key] = _unknown("cannot assess until all three semantic objects exist")

    checks["reported_value_grid"] = (
        {"status": "SUPPORTED", "detail": "primary BLS grid evidence note present; conditional on contracts settling on the reported Employment Situation value"}
        if grid_note_present
        else _unknown("primary BLS grid evidence note missing")
    )

    statuses: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if set(value) >= {"status", "detail"} and isinstance(value.get("status"), str):
                statuses.append(value["status"])
            else:
                for child in value.values():
                    walk(child)

    walk(checks)
    failures = statuses.count("FAIL")
    unknowns = statuses.count("UNKNOWN")

    # SUPPORTED means evidence exists but may still require an alignment check.
    # The mechanism may pass only when every decisive item is an unqualified PASS.
    supported = statuses.count("SUPPORTED")
    mechanism = "MECHANISM_PASS" if failures == 0 and unknowns == 0 and supported == 0 else "BLOCKED_SEMANTICS"

    return {
        "schema_version": 1,
        "task_id": "KALSHI-U3-SEMANTICS-E452",
        "candidate_id": "PAYOFF-IDENTITY-MINING-V1",
        "input_task_id": artifact.get("task_id"),
        "checks": checks,
        "summary": {
            "failures": failures,
            "unknowns": unknowns,
            "supported_needing_manual_alignment": supported,
        },
        "mechanism": mechanism,
        "price_comparison_authorized": mechanism == "MECHANISM_PASS",
        "live_trading": False,
        "paid_actions": False,
        "wallet_actions": False,
        "economic_conclusion": "NO_PROVEN_EDGE",
    }


def main() -> int:
    if not INFILE.exists():
        print(json.dumps({
            "status": "BLOCKED_SEMANTICS",
            "reason": "E451_ARTIFACT_MISSING",
            "input": str(INFILE.relative_to(ROOT)),
            "economic_conclusion": "NO_PROVEN_EDGE",
        }, sort_keys=True))
        return 2

    artifact = json.loads(INFILE.read_text(encoding="utf-8"))
    if not isinstance(artifact, dict):
        raise ValueError("E451 artifact must be a JSON object")

    review = review_artifact(artifact, grid_note_present=GRID_NOTE.exists())
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTFILE.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": review["mechanism"],
        "artifact": str(OUTFILE.relative_to(ROOT)),
        "summary": review["summary"],
        "price_comparison_authorized": review["price_comparison_authorized"],
        "economic_conclusion": "NO_PROVEN_EDGE",
    }, sort_keys=True))
    return 0 if review["mechanism"] == "MECHANISM_PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
