#!/usr/bin/env python3
"""Fail-closed KWI -> Kalshi market-reaction analysis primitives.

This module intentionally does not place orders or infer economic edge. It
aligns point-in-time KWI availability with captured executable market state and
classifies whether a quote/trade reaction is observable with adequate capture
coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

REACTION_OBSERVED = "REACTION_OBSERVED"
NO_REACTION_OBSERVED_WITHIN_WINDOW = "NO_REACTION_OBSERVED_WITHIN_WINDOW"
UNPROVEN_REACTION = "UNPROVEN_REACTION"
ECONOMIC_CONCLUSION = "NO_PROVEN_EDGE"


def _parse_ts_ms(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("timestamp missing")
    if isinstance(value, (int, float)):
        return int(value if value > 1_000_000_000_000 else value * 1000)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp malformed")
    s = value.strip()
    try:
        n = float(s)
    except ValueError:
        n = None
    if n is not None:
        return int(n if n > 1_000_000_000_000 else n * 1000)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return int(dt.timestamp() * 1000)


def parse_ts_ms(value: Any) -> int:
    return _parse_ts_ms(value)


def _dec(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"invalid decimal: {value!r}")


def _best(levels: Any) -> tuple[Optional[Decimal], Optional[Decimal]]:
    if not levels:
        return None, None
    parsed: list[tuple[Decimal, Decimal]] = []
    for level in levels:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            raise ValueError("malformed orderbook level")
        price, qty = _dec(level[0]), _dec(level[1])
        if price is None or qty is None or qty < 0:
            raise ValueError("invalid orderbook level")
        if qty > 0:
            parsed.append((price, qty))
    return max(parsed, key=lambda x: x[0]) if parsed else (None, None)


@dataclass(frozen=True)
class MarketState:
    ticker: str
    ts_ms: int
    yes_bid: Optional[Decimal]
    yes_ask: Optional[Decimal]
    no_bid: Optional[Decimal]
    no_ask: Optional[Decimal]
    yes_bid_qty: Optional[Decimal] = None
    no_bid_qty: Optional[Decimal] = None
    transport: str = "unknown"
    seq: Optional[int] = None

    @property
    def fingerprint(self) -> tuple[Any, ...]:
        return (self.yes_bid, self.yes_ask, self.no_bid, self.no_ask,
                self.yes_bid_qty, self.no_bid_qty)

    def as_json(self) -> dict[str, Any]:
        def s(x: Optional[Decimal]) -> Optional[str]:
            return None if x is None else format(x, "f")
        return {
            "ticker": self.ticker, "ts_ms": self.ts_ms,
            "yes_bid": s(self.yes_bid), "yes_ask": s(self.yes_ask),
            "no_bid": s(self.no_bid), "no_ask": s(self.no_ask),
            "yes_bid_qty": s(self.yes_bid_qty), "no_bid_qty": s(self.no_bid_qty),
            "transport": self.transport, "seq": self.seq,
        }


def market_state_from_rest(ticker: str, ts: Any, payload: dict[str, Any]) -> MarketState:
    ob = payload.get("orderbook_fp") or payload.get("orderbook")
    if not isinstance(ob, dict):
        raise ValueError("orderbook payload missing")
    yes_levels = ob.get("yes_dollars")
    no_levels = ob.get("no_dollars")
    if yes_levels is None and "yes" in ob:
        yes_levels = [[Decimal(str(p)) / 100, q] for p, q in ob.get("yes") or []]
    if no_levels is None and "no" in ob:
        no_levels = [[Decimal(str(p)) / 100, q] for p, q in ob.get("no") or []]
    yes_bid, yes_qty = _best(yes_levels)
    no_bid, no_qty = _best(no_levels)
    one = Decimal("1")
    return MarketState(
        ticker=ticker, ts_ms=_parse_ts_ms(ts),
        yes_bid=yes_bid, yes_ask=None if no_bid is None else one - no_bid,
        no_bid=no_bid, no_ask=None if yes_bid is None else one - yes_bid,
        yes_bid_qty=yes_qty, no_bid_qty=no_qty, transport="rest",
    )


class OrderBook:
    """Deterministic yes/no-bid reconstruction; sequence ambiguity fails closed."""
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.yes: dict[Decimal, Decimal] = {}
        self.no: dict[Decimal, Decimal] = {}
        self.last_seq: Optional[int] = None
        self.ready = False

    def _load_levels(self, target: dict[Decimal, Decimal], levels: Any) -> None:
        target.clear()
        for level in levels or []:
            if not isinstance(level, (list, tuple)) or len(level) < 2:
                raise ValueError("malformed snapshot level")
            p, q = _dec(level[0]), _dec(level[1])
            if p is None or q is None or q < 0:
                raise ValueError("invalid snapshot level")
            if q:
                target[p] = q

    def snapshot(self, envelope: dict[str, Any], recv_ts: Any) -> MarketState:
        if envelope.get("type") != "orderbook_snapshot":
            raise ValueError("not orderbook_snapshot")
        msg = envelope.get("msg") or {}
        if msg.get("market_ticker") != self.ticker:
            raise ValueError("ticker mismatch")
        seq = envelope.get("seq")
        if not isinstance(seq, int):
            raise ValueError("snapshot seq missing")
        self._load_levels(self.yes, msg.get("yes_dollars_fp") or [])
        self._load_levels(self.no, msg.get("no_dollars_fp") or [])
        self.last_seq, self.ready = seq, True
        return self.state(recv_ts, seq)

    def delta(self, envelope: dict[str, Any], recv_ts: Any) -> MarketState:
        if not self.ready or envelope.get("type") != "orderbook_delta":
            raise ValueError("delta before snapshot or wrong type")
        msg = envelope.get("msg") or {}
        if msg.get("market_ticker") != self.ticker:
            raise ValueError("ticker mismatch")
        seq = envelope.get("seq")
        if not isinstance(seq, int) or self.last_seq is None or seq != self.last_seq + 1:
            raise ValueError(f"sequence gap: {self.last_seq}->{seq}")
        side = msg.get("side")
        if side not in ("yes", "no"):
            raise ValueError("invalid side")
        price, delta = _dec(msg.get("price_dollars")), _dec(msg.get("delta_fp"))
        if price is None or delta is None:
            raise ValueError("delta fields missing")
        target = self.yes if side == "yes" else self.no
        new_qty = target.get(price, Decimal("0")) + delta
        if new_qty < 0:
            raise ValueError("negative level after delta")
        if new_qty == 0:
            target.pop(price, None)
        else:
            target[price] = new_qty
        self.last_seq = seq
        return self.state(recv_ts, seq)

    def state(self, ts: Any, seq: Optional[int] = None) -> MarketState:
        yes_bid, yes_qty = _best([[p, q] for p, q in self.yes.items()])
        no_bid, no_qty = _best([[p, q] for p, q in self.no.items()])
        one = Decimal("1")
        return MarketState(
            ticker=self.ticker, ts_ms=_parse_ts_ms(ts), yes_bid=yes_bid,
            yes_ask=None if no_bid is None else one - no_bid, no_bid=no_bid,
            no_ask=None if yes_bid is None else one - yes_bid,
            yes_bid_qty=yes_qty, no_bid_qty=no_qty, transport="ws", seq=seq,
        )


def extract_kwi_events(manifests: Iterable[dict[str, Any]], city: str) -> list[dict[str, Any]]:
    """Extract E390 first-decision-eligible incomplete signals point-in-time."""
    rows: list[tuple[int, dict[str, Any]]] = []
    for manifest in manifests:
        try:
            retrieved_ms = _parse_ts_ms(manifest.get("retrieved_at"))
        except ValueError:
            continue
        for row in manifest.get("cities") or []:
            if not isinstance(row, dict) or str(row.get("city", "")).lower() != city.lower():
                continue
            incomplete, previous = row.get("latest_incomplete") or {}, row.get("latest_complete") or {}
            if not isinstance(incomplete, dict) or not isinstance(previous, dict):
                continue
            try:
                target_t = int(incomplete.get("t")); previous_t = int(previous.get("t"))
                previous_v = _dec(previous.get("v")); expected = int(previous.get("contributors"))
            except (TypeError, ValueError):
                continue
            if previous_v is None or previous_t >= target_t or expected <= 0:
                continue
            temps: list[Decimal] = []
            for station in incomplete.get("stations") or []:
                if not isinstance(station, dict):
                    continue
                try:
                    temp = _dec(station.get("temp_f"))
                except ValueError:
                    continue
                if temp is not None:
                    temps.append(temp)
            if len(temps) != expected:
                continue
            mean = sum(temps, Decimal("0")) / Decimal(len(temps))
            rows.append((retrieved_ms, {
                "city": city, "config_version": row.get("config_version"), "kwi_t": target_t,
                "signal_v": format(mean, "f"), "previous_t": previous_t,
                "previous_v": format(previous_v, "f"), "station_count": len(temps),
                "expected_contributors": expected,
                "station_values": [format(x, "f") for x in temps],
            }))
    rows.sort(key=lambda x: x[0])
    out: list[dict[str, Any]] = []
    last_fingerprint: dict[int, tuple[str, ...]] = {}
    for retrieved_ms, event in rows:
        target_t = int(event["kwi_t"]); fp = tuple(event["station_values"])
        if target_t not in last_fingerprint:
            kind = "first_decision_eligible"
        elif last_fingerprint[target_t] == fp:
            continue
        else:
            kind = "revision"
        prior_fp = last_fingerprint.get(target_t); last_fingerprint[target_t] = fp
        out.append({**event, "kind": kind, "available_at_ms": retrieved_ms,
                    "prior_station_values": list(prior_fp) if prior_fp is not None else None})
    return out


def _gap_straddles(gap: dict[str, Any], start_ms: int, end_ms: int) -> bool:
    try:
        gs, ge = _parse_ts_ms(gap["start"]), _parse_ts_ms(gap["end"])
    except (KeyError, ValueError):
        return True
    return not (ge < start_ms or gs > end_ms)


def analyze_reaction(kwi_event: dict[str, Any], states: Iterable[MarketState],
                     trades: Iterable[dict[str, Any]] = (), gaps: Iterable[dict[str, Any]] = (),
                     coverage_ms: Iterable[int] = (), *, window_ms: int = 30_000,
                     max_pre_age_ms: int = 5_000, max_state_gap_ms: int = 5_000) -> dict[str, Any]:
    t0 = int(kwi_event["available_at_ms"]); ordered = list(states)
    coverage_points = [int(x) for x in coverage_ms]; reasons: list[str] = []
    if not ordered:
        reasons.append("NO_MARKET_STATES")
    for a, b in zip(ordered, ordered[1:]):
        if b.ts_ms < a.ts_ms:
            reasons.append("OUT_OF_ORDER_MARKET_STATE"); break
    ordered = sorted(ordered, key=lambda x: x.ts_ms)
    pre, post = [s for s in ordered if s.ts_ms <= t0], [s for s in ordered if s.ts_ms > t0]
    if not pre:
        reasons.append("NO_PRE_EVENT_EXECUTABLE_STATE")
    else:
        baseline = pre[-1]
        if baseline.transport == "ws":
            recent = [baseline.ts_ms] + [x for x in coverage_points if x <= t0]
            if t0 - max(recent) > max_pre_age_ms:
                reasons.append("PRE_EVENT_WS_COVERAGE_TOO_OLD")
        elif t0 - baseline.ts_ms > max_pre_age_ms:
            reasons.append("PRE_EVENT_STATE_TOO_OLD")
    end = t0 + window_ms
    if any(_gap_straddles(g, t0 - max_pre_age_ms, end) for g in gaps):
        reasons.append("CAPTURE_GAP_STRADDLES_WINDOW")
    relevant = [s for s in ordered if t0 - max_pre_age_ms <= s.ts_ms <= end]
    if relevant and any(s.transport == "rest" for s in relevant):
        for a, b in zip(relevant, relevant[1:]):
            if a.transport == b.transport == "rest" and b.ts_ms - a.ts_ms > max_state_gap_ms:
                reasons.append("MARKET_STATE_GAP_TOO_LARGE"); break
    if reasons:
        return {"status": UNPROVEN_REACTION, "economic_conclusion": ECONOMIC_CONCLUSION,
                "reasons": sorted(set(reasons)), "kwi_event": kwi_event}
    baseline = pre[-1]; candidates: list[tuple[int, str, Any]] = []
    for s in post:
        if s.ts_ms > end: break
        if s.fingerprint != baseline.fingerprint:
            candidates.append((s.ts_ms, "book", s))
    for trade in trades:
        try:
            ticker = trade.get("ticker") or trade.get("market_ticker")
            trade_ms = _parse_ts_ms(trade.get("ts_ms", trade.get("created_time", trade.get("ts"))))
        except (AttributeError, ValueError):
            continue
        if ticker == baseline.ticker and t0 < trade_ms <= end:
            candidates.append((trade_ms, "trade", trade))
    if candidates:
        reaction_ms, kind, obj = min(candidates, key=lambda x: x[0])
        return {"status": REACTION_OBSERVED, "economic_conclusion": ECONOMIC_CONCLUSION,
                "reaction_kind": kind, "latency_ms": reaction_ms - t0, "kwi_event": kwi_event,
                "baseline": baseline.as_json(),
                "reaction_state": obj.as_json() if kind == "book" else obj}
    coverage_end = max([s.ts_ms for s in ordered] + coverage_points, default=-1)
    if coverage_end < end:
        return {"status": UNPROVEN_REACTION, "economic_conclusion": ECONOMIC_CONCLUSION,
                "reasons": ["CAPTURE_ENDS_BEFORE_WINDOW"], "kwi_event": kwi_event,
                "baseline": baseline.as_json()}
    return {"status": NO_REACTION_OBSERVED_WITHIN_WINDOW,
            "economic_conclusion": ECONOMIC_CONCLUSION, "latency_lower_bound_ms": window_ms,
            "kwi_event": kwi_event, "baseline": baseline.as_json()}
