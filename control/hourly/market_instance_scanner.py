from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from itertools import combinations
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "knowledge/runs/market_instance_scan"
STATE = ROOT / "knowledge/recon/market_instance_state.json"
DEFAULT_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
DEFAULT_MAX_PAGES = 30
DEFAULT_TIMEOUT_SECONDS = 20
MAX_ROUTED_FINDINGS = 80

PROOF_PENDING = "API_RELATION_PROVED_RULE_EXCEPTION_REVIEW_PENDING"
PROOF_EXACT = "EXACT_DECLARED_SEMANTICS_MATCH"
PROOF_SAME_MARKET = "SAME_BINARY_MARKET_COMPLEMENT"
PROOF_EVENT_MUTEX = "EVENT_MUTUAL_EXCLUSION_DECLARED"
NO_NET_CLAIM = "NO_PROVEN_EDGE"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _request_json(base_url: str, endpoint: str, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    query = urlencode({k: v for k, v in params.items() if v is not None})
    url = base_url.rstrip("/") + endpoint + ("?" + query if query else "")
    req = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "prediction-research-os-market-instance-scanner/1.0",
        },
    )
    with urlopen(req, timeout=timeout) as response:  # nosec B310 - fixed HTTPS public API by default
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"unexpected JSON shape from {endpoint}")
    return payload


def _paginate(
    base_url: str,
    endpoint: str,
    item_key: str,
    params: dict[str, Any],
    *,
    timeout: int,
    max_pages: int,
) -> tuple[list[dict[str, Any]], bool]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    exhausted = False
    for _ in range(max_pages):
        page_params = dict(params)
        if cursor:
            page_params["cursor"] = cursor
        payload = _request_json(base_url, endpoint, page_params, timeout)
        page = payload.get(item_key, [])
        if isinstance(page, list):
            items.extend(x for x in page if isinstance(x, dict))
        cursor = payload.get("cursor") or None
        if not cursor:
            exhausted = True
            break
    return items, exhausted


def fetch_public_snapshot(
    *,
    base_url: str | None = None,
    max_pages: int | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Fetch public, unauthenticated open Kalshi events/markets.

    This function is strictly read-only. It never touches order, portfolio, or
    authenticated endpoints. The event endpoint is used for mutual-exclusion
    metadata; the markets endpoint is the canonical market-instance inventory.
    """
    base = (base_url or os.environ.get("KALSHI_PUBLIC_API_BASE") or DEFAULT_BASE_URL).rstrip("/")
    pages = max_pages or int(os.environ.get("KALSHI_MARKET_SCAN_MAX_PAGES", DEFAULT_MAX_PAGES))

    events, events_exhausted = _paginate(
        base,
        "/events",
        "events",
        {"limit": 200, "status": "open", "with_nested_markets": "true"},
        timeout=timeout,
        max_pages=pages,
    )
    markets, markets_exhausted = _paginate(
        base,
        "/markets",
        "markets",
        {"limit": 1000, "status": "open"},
        timeout=timeout,
        max_pages=pages,
    )

    return {
        "retrieved_at": _utcnow(),
        "base_url": base,
        "events": events,
        "markets": markets,
        "coverage": {
            "events_pages_exhausted": events_exhausted,
            "markets_pages_exhausted": markets_exhausted,
            "max_pages": pages,
            "complete_open_universe": bool(events_exhausted and markets_exhausted),
        },
        "safety": {
            "public_read_only": True,
            "authentication_used": False,
            "live_trading": False,
            "orders": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    }


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _price_cents(raw: dict[str, Any], side: str, quote: str) -> Decimal | None:
    dollars = _decimal(raw.get(f"{side}_{quote}_dollars"))
    if dollars is not None:
        return dollars * Decimal(100)
    cents = _decimal(raw.get(f"{side}_{quote}"))
    if cents is not None:
        return cents
    return None


def _semantic_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_type": raw.get("market_type"),
        "strike_type": raw.get("strike_type"),
        "floor_strike": raw.get("floor_strike"),
        "cap_strike": raw.get("cap_strike"),
        "custom_strike": raw.get("custom_strike"),
        "functional_strike": raw.get("functional_strike"),
        "expiration_time": raw.get("expiration_time"),
        "rules_primary": raw.get("rules_primary"),
        "rules_secondary": raw.get("rules_secondary"),
    }


def normalize_market(raw: dict[str, Any], event_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    event = event_meta or {}
    semantics = _semantic_payload(raw)
    return {
        "ticker": str(raw.get("ticker") or ""),
        "event_ticker": str(raw.get("event_ticker") or event.get("event_ticker") or ""),
        "series_ticker": str(raw.get("series_ticker") or event.get("series_ticker") or ""),
        "title": raw.get("title"),
        "status": raw.get("status"),
        "market_type": raw.get("market_type"),
        "strike_type": raw.get("strike_type"),
        "floor_strike": _decimal(raw.get("floor_strike")),
        "cap_strike": _decimal(raw.get("cap_strike")),
        "custom_strike": raw.get("custom_strike"),
        "functional_strike": raw.get("functional_strike"),
        "close_time": raw.get("close_time"),
        "expiration_time": raw.get("expiration_time"),
        "rules_primary": raw.get("rules_primary"),
        "rules_secondary": raw.get("rules_secondary"),
        "settlement_timer_seconds": raw.get("settlement_timer_seconds"),
        "can_close_early": raw.get("can_close_early"),
        "yes_bid_cents": _price_cents(raw, "yes", "bid"),
        "yes_ask_cents": _price_cents(raw, "yes", "ask"),
        "no_bid_cents": _price_cents(raw, "no", "bid"),
        "no_ask_cents": _price_cents(raw, "no", "ask"),
        "event_mutually_exclusive": bool(event.get("mutually_exclusive", False)),
        "event_collateral_return_type": event.get("collateral_return_type"),
        "semantic_sha256": _sha(semantics),
    }


def normalize_snapshot(snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    events = {
        str(e.get("event_ticker")): e
        for e in snapshot.get("events", [])
        if isinstance(e, dict) and e.get("event_ticker")
    }
    markets_by_ticker: dict[str, dict[str, Any]] = {}

    for raw in snapshot.get("markets", []):
        if not isinstance(raw, dict) or not raw.get("ticker"):
            continue
        norm = normalize_market(raw, events.get(str(raw.get("event_ticker"))))
        markets_by_ticker[norm["ticker"]] = norm

    for event in events.values():
        for raw in event.get("markets", []) or []:
            if not isinstance(raw, dict) or not raw.get("ticker"):
                continue
            ticker = str(raw["ticker"])
            if ticker not in markets_by_ticker:
                markets_by_ticker[ticker] = normalize_market(raw, event)

    return list(markets_by_ticker.values()), events


def _relation_id(kind: str, tickers: list[str]) -> str:
    return "KALREL-" + hashlib.sha256((kind + "|" + "|".join(sorted(tickers))).encode()).hexdigest()[:18]


def _basket_screen(legs: list[tuple[dict[str, Any], str]], guaranteed_payout_cents: Decimal) -> dict[str, Any]:
    asks: list[dict[str, Any]] = []
    total = Decimal(0)
    for market, side in legs:
        ask = market.get(f"{side}_ask_cents")
        asks.append({"ticker": market["ticker"], "side": side.upper(), "ask_cents": str(ask) if ask is not None else None})
        if ask is None:
            return {
                "status": "PRICE_INCOMPLETE",
                "legs": asks,
                "guaranteed_payout_cents": str(guaranteed_payout_cents),
                "gross_cost_cents": None,
                "gross_margin_cents": None,
                "net_ev_cents": None,
                "requires": ["synchronized executable L2", "fees", "depth", "partial-fill/slippage review"],
            }
        total += ask
    margin = guaranteed_payout_cents - total
    return {
        "status": "GROSS_POSITIVE_PENDING_FEES_DEPTH" if margin > 0 else "NO_GROSS_EDGE_AT_TOP_OF_BOOK",
        "legs": asks,
        "guaranteed_payout_cents": str(guaranteed_payout_cents),
        "gross_cost_cents": str(total),
        "gross_margin_cents": str(margin),
        "net_ev_cents": None,
        "requires": ["synchronized executable L2", "fees", "depth", "partial-fill/slippage review"],
    }


def _finding(
    kind: str,
    markets: list[dict[str, Any]],
    *,
    proof_basis: str,
    relation: str,
    screens: list[dict[str, Any]],
    rule_exception_review_required: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tickers = [m["ticker"] for m in markets]
    gross_positive = any(x.get("status") == "GROSS_POSITIVE_PENDING_FEES_DEPTH" for x in screens)
    return {
        "relation_id": _relation_id(kind, tickers),
        "relation_type": kind,
        "tickers": sorted(tickers),
        "event_tickers": sorted({m.get("event_ticker") for m in markets if m.get("event_ticker")}),
        "series_tickers": sorted({m.get("series_ticker") for m in markets if m.get("series_ticker")}),
        "relation": relation,
        "semantic_proof": {
            "status": proof_basis,
            "rule_exception_review_required": rule_exception_review_required,
            "price_used_for_proof": False,
        },
        "economic_screens": screens,
        "gross_positive_screen": gross_positive,
        "net_positive_ev_proven": False,
        "economic_conclusion": NO_NET_CLAIM,
        "routing": ["algebra", "settlement", "microstructure"] if gross_positive else ["algebra", "settlement"],
        "metadata": metadata or {},
    }


def _same_expiration(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return bool(a.get("expiration_time") and a.get("expiration_time") == b.get("expiration_time"))


def _binary(markets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [m for m in markets if m.get("market_type") in {None, "", "binary"}]


def _exact_semantics_key(m: dict[str, Any]) -> tuple[Any, ...]:
    return (
        m.get("market_type"),
        m.get("strike_type"),
        m.get("floor_strike"),
        m.get("cap_strike"),
        json.dumps(m.get("custom_strike"), sort_keys=True, default=str),
        m.get("functional_strike"),
        m.get("expiration_time"),
        m.get("rules_primary"),
        m.get("rules_secondary"),
    )


def _custom_values(value: Any) -> set[str] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        vals: list[Any] = []
        for v in value.values():
            vals.extend(v if isinstance(v, list) else [v])
        return {json.dumps(v, sort_keys=True, default=str) for v in vals}
    if isinstance(value, list):
        return {json.dumps(v, sort_keys=True, default=str) for v in value}
    return {json.dumps(value, sort_keys=True, default=str)}


def find_relations(markets: list[dict[str, Any]], events: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    findings: dict[str, dict[str, Any]] = {}
    active_binary = _binary(markets)

    for m in active_binary:
        if not m.get("ticker"):
            continue
        screen = _basket_screen([(m, "yes"), (m, "no")], Decimal(100))
        f = _finding(
            "COMPLEMENT",
            [m],
            proof_basis=PROOF_SAME_MARKET,
            relation="YES + NO pays 100 cents for the same binary market (subject to venue settlement/void mechanics review).",
            screens=[screen],
            rule_exception_review_required=True,
        )
        findings[f["relation_id"]] = f

    by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in active_binary:
        if m.get("event_ticker"):
            by_event[m["event_ticker"]].append(m)

    for event_ticker, group in by_event.items():
        event = events.get(event_ticker, {})

        if event.get("mutually_exclusive") is True and len(group) >= 2:
            payout = Decimal(100 * (len(group) - 1))
            screen = _basket_screen([(m, "no") for m in group], payout)
            f = _finding(
                "MUTUALLY_EXCLUSIVE_SET",
                group,
                proof_basis=PROOF_EVENT_MUTEX,
                relation=f"At most one YES across {len(group)} event markets; all-NO basket has minimum payout {payout} cents.",
                screens=[screen],
                metadata={"event_ticker": event_ticker, "market_count": len(group)},
            )
            findings[f["relation_id"]] = f

        for strike_type in ("greater", "greater_or_equal", "less", "less_or_equal"):
            thresholded = [
                m for m in group
                if m.get("strike_type") == strike_type
                and (m.get("floor_strike") is not None or m.get("cap_strike") is not None)
            ]
            for a, b in combinations(thresholded, 2):
                if not _same_expiration(a, b):
                    continue
                if strike_type.startswith("greater"):
                    ta, tb = a["floor_strike"], b["floor_strike"]
                    if ta == tb:
                        continue
                    dominator, dominated = (a, b) if ta < tb else (b, a)
                else:
                    ta, tb = a["cap_strike"], b["cap_strike"]
                    if ta == tb:
                        continue
                    dominator, dominated = (a, b) if ta > tb else (b, a)

                screen = _basket_screen([(dominator, "yes"), (dominated, "no")], Decimal(100))
                f = _finding(
                    "NESTED_DOMINANCE",
                    [dominator, dominated],
                    proof_basis=PROOF_PENDING,
                    relation=f"{dominator['ticker']} YES state contains {dominated['ticker']} YES state under declared {strike_type} strikes.",
                    screens=[screen],
                    metadata={
                        "strike_type": strike_type,
                        "dominator": dominator["ticker"],
                        "dominated": dominated["ticker"],
                    },
                )
                findings[f["relation_id"]] = f

        ranges = [
            m for m in group
            if m.get("strike_type") == "between"
            and m.get("floor_strike") is not None
            and m.get("cap_strike") is not None
        ]
        for a, b in combinations(ranges, 2):
            if not _same_expiration(a, b):
                continue
            disjoint = a["cap_strike"] < b["floor_strike"] or b["cap_strike"] < a["floor_strike"]
            if not disjoint:
                continue
            screen = _basket_screen([(a, "no"), (b, "no")], Decimal(100))
            f = _finding(
                "MUTUALLY_EXCLUSIVE_PAIR",
                [a, b],
                proof_basis=PROOF_PENDING,
                relation="Disjoint inclusive strike ranges cannot both settle YES.",
                screens=[screen],
                metadata={"basis": "disjoint_between_ranges"},
            )
            findings[f["relation_id"]] = f

        custom = [m for m in group if m.get("strike_type") == "custom" and m.get("custom_strike") is not None]
        for a, b in combinations(custom, 2):
            if not _same_expiration(a, b):
                continue
            av, bv = _custom_values(a.get("custom_strike")), _custom_values(b.get("custom_strike"))
            if not av or not bv or not av.isdisjoint(bv):
                continue
            screen = _basket_screen([(a, "no"), (b, "no")], Decimal(100))
            f = _finding(
                "MUTUALLY_EXCLUSIVE_PAIR",
                [a, b],
                proof_basis=PROOF_PENDING,
                relation="Disjoint custom expiration-value sets cannot both settle YES.",
                screens=[screen],
                metadata={"basis": "disjoint_custom_values"},
            )
            findings[f["relation_id"]] = f

    by_semantics: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for m in active_binary:
        if m.get("rules_primary") and m.get("expiration_time"):
            by_semantics[_exact_semantics_key(m)].append(m)
    for group in by_semantics.values():
        if len(group) < 2:
            continue
        for a, b in combinations(group, 2):
            screens = [
                _basket_screen([(a, "yes"), (b, "no")], Decimal(100)),
                _basket_screen([(b, "yes"), (a, "no")], Decimal(100)),
            ]
            f = _finding(
                "DECLARED_EQUIVALENCE",
                [a, b],
                proof_basis=PROOF_EXACT,
                relation="API-declared payout semantics, rules text and expiration match exactly; independent rule/source review still required.",
                screens=screens,
                metadata={"cross_series": a.get("series_ticker") != b.get("series_ticker")},
            )
            findings[f["relation_id"]] = f

    return sorted(findings.values(), key=lambda x: (not x["gross_positive_screen"], x["relation_type"], x["relation_id"]))


def _state_changes(markets: list[dict[str, Any]], state_path: Path = STATE) -> dict[str, Any]:
    previous = _load_json(state_path, {"semantic_hash_by_ticker": {}})
    old = previous.get("semantic_hash_by_ticker", {})
    current = {m["ticker"]: m["semantic_sha256"] for m in markets if m.get("ticker")}
    new = sorted(set(current) - set(old))
    removed = sorted(set(old) - set(current))
    changed = sorted(t for t in set(current) & set(old) if current[t] != old[t])
    _save_json(state_path, {
        "updated_at": _utcnow(),
        "semantic_hash_by_ticker": current,
        "note": "Semantic hashes exclude prices; price screens still run every cycle.",
    })
    return {
        "new_market_count": len(new),
        "removed_market_count": len(removed),
        "semantic_change_count": len(changed),
        "new_market_sample": new[:25],
        "removed_market_sample": removed[:25],
        "semantic_change_sample": changed[:25],
    }


def scan_snapshot(snapshot: dict[str, Any], *, state_path: Path | None = None) -> dict[str, Any]:
    markets, events = normalize_snapshot(snapshot)
    findings = find_relations(markets, events)
    gross_positive = [f for f in findings if f.get("gross_positive_screen")]
    changes = _state_changes(markets, state_path or STATE)
    return {
        "schema": "PVA_KALSHI_MARKET_INSTANCE_SCAN_V1",
        "retrieved_at": snapshot.get("retrieved_at"),
        "source": snapshot.get("base_url"),
        "coverage": snapshot.get("coverage", {}),
        "objects_checked": {
            "markets": len(markets),
            "events": len(events),
        },
        "change_detection": changes,
        "relation_count": len(findings),
        "relation_type_counts": {
            kind: sum(1 for f in findings if f["relation_type"] == kind)
            for kind in sorted({f["relation_type"] for f in findings})
        },
        "gross_positive_screen_count": len(gross_positive),
        "findings": findings,
        "economic_conclusion": NO_NET_CLAIM,
        "proof_note": "Gross-positive screens are not net EV claims. Fees, synchronized executable L2/depth, fills and rule exceptions remain mandatory.",
        "safety": {
            "research_only": True,
            "live_trading": False,
            "orders": False,
            "paid_actions": False,
            "wallet_actions": False,
        },
    }


def routing_evidence(scan: dict[str, Any], max_items: int = MAX_ROUTED_FINDINGS) -> dict[str, list[dict[str, Any]]]:
    findings = list(scan.get("findings", []))
    findings.sort(key=lambda x: (not x.get("gross_positive_screen"), x.get("relation_type", ""), x.get("relation_id", "")))
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings[:max_items]:
        relation_id = finding["relation_id"]
        margins = [
            s.get("gross_margin_cents")
            for s in finding.get("economic_screens", [])
            if s.get("gross_margin_cents") is not None
        ]
        snippet = (
            f"Kalshi concrete market-instance relation {relation_id}: "
            f"type={finding['relation_type']}; tickers={','.join(finding['tickers'])}; "
            f"semantic_status={finding['semantic_proof']['status']}; "
            f"gross_margins_cents={margins}; net_positive_ev_proven=false. "
            f"Independent rule-exception, fees, executable L2/depth and fill review required."
        )
        evidence = {
            "source_id": "kalshi-market-instance-scanner",
            "document_sha256": _sha(finding),
            "retrieved_at": scan.get("retrieved_at"),
            "snippet": snippet,
            "market_relation": finding,
            "point_in_time": True,
        }
        for capability in finding.get("routing", []):
            out[capability].append(evidence)
    return dict(out)


def inject_routing(routing: dict[str, Any], scan: dict[str, Any]) -> dict[str, Any]:
    additions = routing_evidence(scan)
    for capability, evidence in additions.items():
        role = routing.setdefault(capability, {})
        role.setdefault("evidence", [])
        role["evidence"].extend(evidence)
    return routing


def run(
    run_id: str,
    *,
    snapshot: dict[str, Any] | None = None,
    base_url: str | None = None,
    max_pages: int | None = None,
) -> tuple[dict[str, Any], Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"{run_id}.json"
    try:
        snap = snapshot or fetch_public_snapshot(base_url=base_url, max_pages=max_pages)
        result = scan_snapshot(snap)
        result["run_id"] = run_id
        result["status"] = "OK"
    except Exception as exc:
        result = {
            "schema": "PVA_KALSHI_MARKET_INSTANCE_SCAN_V1",
            "run_id": run_id,
            "retrieved_at": _utcnow(),
            "status": "BLOCKED",
            "blocker": f"{type(exc).__name__}: {exc}",
            "relation_count": 0,
            "gross_positive_screen_count": 0,
            "findings": [],
            "economic_conclusion": NO_NET_CLAIM,
            "safety": {
                "research_only": True,
                "live_trading": False,
                "orders": False,
                "paid_actions": False,
                "wallet_actions": False,
            },
        }
    _save_json(out_path, result)
    return result, out_path


if __name__ == "__main__":
    data, path = run("manual-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    print(json.dumps({
        "status": data.get("status"),
        "objects_checked": data.get("objects_checked"),
        "relation_count": data.get("relation_count"),
        "gross_positive_screen_count": data.get("gross_positive_screen_count"),
        "economic_conclusion": data.get("economic_conclusion"),
        "ref": str(path),
    }, sort_keys=True))
