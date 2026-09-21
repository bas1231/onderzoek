#!/usr/bin/env python3
"""Read-only market capture helpers for E401.

The helpers write immutable JSONL evidence only. They expose no order, portfolio,
wallet, or paid-service mutation capability.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from control.weather.kwi_market_reaction_e401 import OrderBook, market_state_from_rest


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        fh.flush()


def recv_ms() -> int:
    return time.time_ns() // 1_000_000


def capture_rest_snapshot(ticker: str, payload: dict[str, Any], out: Path, *, received_at_ms: int | None = None) -> dict[str, Any]:
    ts = recv_ms() if received_at_ms is None else int(received_at_ms)
    state = market_state_from_rest(ticker, ts, payload)
    row = state.as_json()
    row["capture_kind"] = "rest_snapshot"
    append_jsonl(out, row)
    return row


class WsEvidenceRecorder:
    """Stateful orderbook recorder with explicit gap evidence."""
    def __init__(self, ticker: str, state_path: Path, gap_path: Path, coverage_path: Path):
        self.ticker = ticker
        self.book = OrderBook(ticker)
        self.state_path = state_path
        self.gap_path = gap_path
        self.coverage_path = coverage_path

    def heartbeat(self, *, received_at_ms: int | None = None) -> None:
        ts = recv_ms() if received_at_ms is None else int(received_at_ms)
        append_jsonl(self.coverage_path, {"ts_ms": ts, "ticker": self.ticker, "kind": "coverage"})

    def record_gap(self, start_ms: int, end_ms: int, reason: str) -> None:
        append_jsonl(self.gap_path, {"start": int(start_ms), "end": int(end_ms), "ticker": self.ticker, "reason": reason})

    def ingest(self, envelope: dict[str, Any], *, received_at_ms: int | None = None) -> dict[str, Any] | None:
        ts = recv_ms() if received_at_ms is None else int(received_at_ms)
        kind = envelope.get("type")
        try:
            if kind == "orderbook_snapshot":
                state = self.book.snapshot(envelope, ts)
            elif kind == "orderbook_delta":
                state = self.book.delta(envelope, ts)
            else:
                return None
        except ValueError as exc:
            self.record_gap(ts, ts, f"{kind}:{exc}")
            raise
        row = state.as_json()
        row["capture_kind"] = kind
        append_jsonl(self.state_path, row)
        self.heartbeat(received_at_ms=ts)
        return row
