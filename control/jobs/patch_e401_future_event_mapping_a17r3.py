#!/usr/bin/env python3
"""Patch E401 signal->market linkage to nearest pre-discovered future hourly event.

This job changes only the E401 linker and its focused regression test, validates
locally, then commits/pushes those two files. No trading, wallet, paid action, or
credential mutation is performed.
"""
from __future__ import annotations

from pathlib import Path
import json
import py_compile
import subprocess
import sys

ROOT = Path.cwd()
SRC = ROOT / "control/weather/e401_sync_linker.py"
TEST = ROOT / "control/weather/test_e401_sync_linker.py"

result = {
    "task": "EDGE-HUNTER-KWI-FUTURE-EVENT-MAPPING-E401A17R3",
    "live_trading": False,
    "paid_action": False,
    "wallet_action": False,
    "economic_conclusion": "NO_PROVEN_EDGE",
    "tests_pass": False,
    "a17_pass": False,
    "committed": False,
    "pushed": False,
}


def run(*args, timeout=120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


branch = run("git", "branch", "--show-current").stdout.strip()
if branch != "main":
    result["status"] = "BLOCKED_NOT_MAIN"
    result["branch"] = branch
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(10)

staged = run("git", "diff", "--cached", "--name-only").stdout.strip()
if staged:
    result["status"] = "BLOCKED_PREEXISTING_STAGED_CHANGES"
    result["staged"] = staged.splitlines()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(11)

source = SRC.read_text(encoding="utf-8")

helper_anchor = '''def event_matches_target(city: str, event_ticker: str, kwi_t) -> bool:\n    return event_local_hour(event_ticker) == target_local_hour(city, kwi_t)\n'''
helper_insert = helper_anchor + '''\n\ndef event_target_ms(event_ticker: str) -> int | None:\n    \"\"\"Return the exact KXTEMP market target time encoded in the ticker.\n\n    Kalshi hourly temperature market titles use Eastern Time (EDT/EST); the\n    ticker's terminal hour is that exact market target hour.\n    \"\"\"\n    parsed = event_local_hour(event_ticker)\n    if parsed is None:\n        return None\n    year, month, day, hour = parsed\n    try:\n        dt = datetime(year, month, day, hour, 0, 0, tzinfo=ZoneInfo(\"America/New_York\"))\n    except Exception:\n        return None\n    return int(dt.timestamp() * 1000)\n'''
if "def event_target_ms(" not in source:
    if helper_anchor not in source:
        raise RuntimeError("helper anchor not found")
    source = source.replace(helper_anchor, helper_insert, 1)

start = source.index("def matching_event_snapshot(")
end = source.index("\ndef relevant_logs(", start)
new_matching = '''def matching_event_snapshot(cycles: list[dict], city: str, kwi_event: dict):\n    \"\"\"Nearest future hourly event known before signal availability.\n\n    A Weather Index point is a minute-resolution observation, not the hourly\n    contract's settlement timestamp. For reaction analysis, select the nearest\n    hourly target still in the future at signal availability, using only event\n    discovery snapshots that already existed before that signal. For one ticker,\n    the latest pre-signal discovery snapshot wins.\n    \"\"\"\n    t0 = int(kwi_event[\"available_at_ms\"])\n    by_ticker = {}\n    for cycle in cycles:\n        discovery_ms = int(cycle[\"discovery_ms\"])\n        if discovery_ms > t0:\n            continue\n        for row in cycle[\"discovery\"].get(\"series\") or []:\n            if str(row.get(\"city\", \"\")).lower() != city:\n                continue\n            for event in row.get(\"events\") or []:\n                ticker = event.get(\"event_ticker\")\n                target_ms = event_target_ms(ticker) if ticker else None\n                tickers = sorted(set(event.get(\"market_tickers\") or []))\n                if target_ms is None or target_ms <= t0 or not tickers:\n                    continue\n                prev = by_ticker.get(ticker)\n                if prev is None or discovery_ms > prev[0]:\n                    by_ticker[ticker] = (discovery_ms, target_ms, event, tickers)\n    if not by_ticker:\n        return None\n    ticker, (discovery_ms, target_ms, event, tickers) = min(\n        by_ticker.items(),\n        key=lambda item: (item[1][1], -item[1][0], item[0]),\n    )\n    return {\n        \"event_ticker\": ticker,\n        \"market_tickers\": tickers,\n        \"event_target_at_ms\": target_ms,\n        \"event_discovered_at_ms\": discovery_ms,\n        \"horizon_to_settlement_ms\": target_ms - t0,\n    }\n\n'''
source = source[:start] + new_matching + source[end + 1:]
source = source.replace(
    '"reasons": ["NO_MATCHING_PRE_SIGNAL_HOURLY_EVENT_DISCOVERY"],',
    '"reasons": ["NO_PRE_SIGNAL_FUTURE_HOURLY_EVENT_DISCOVERY"],',
    1,
)
source = source.replace(
    '        "event_ticker": event_ticker,\n        "bucket_count": len(tickers),',
    '        "event_ticker": event_ticker,\n        "event_target_at_ms": event_snapshot.get("event_target_at_ms"),\n        "event_discovered_at_ms": event_snapshot.get("event_discovered_at_ms"),\n        "horizon_to_settlement_ms": event_snapshot.get("horizon_to_settlement_ms"),\n        "bucket_count": len(tickers),',
    1,
)
source = source.replace(
    '            "The hourly event must have been discovered at or before signal availability.",',
    '            "The linked hourly event must have been discovered at or before signal availability and its exact target time must still be in the future.",\n            "Among eligible pre-signal discoveries, the nearest future hourly target is selected; KWI minute timestamps are never treated as settlement timestamps.",',
    1,
)
SRC.write_text(source, encoding="utf-8")

TEST.write_text('''#!/usr/bin/env python3\nfrom datetime import datetime\nimport sys\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[2]\nsys.path.insert(0, str(ROOT / "control" / "weather"))\n\nimport e401_sync_linker as m\n\n\ndef epoch_ms(iso: str) -> int:\n    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)\n\n\ndef discovery(city, events):\n    return {"series": [{"city": city, "events": events}]}\n\n\ndef evt(ticker, tickers):\n    return {"event_ticker": ticker, "market_tickers": tickers}\n\n\ndef test_ticker_hour_is_exact_eastern_market_time():\n    # Sep 21 is EDT: 13:00 ET == 17:00 UTC, including Chicago series.\n    assert m.event_target_ms("KXTEMPMIAH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")\n    assert m.event_target_ms("KXTEMPNYCH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")\n    assert m.event_target_ms("KXTEMPCHIH-26SEP2113") == epoch_ms("2026-09-21T17:00:00Z")\n\n\ndef test_nearest_future_pre_signal_event_is_selected():\n    signal_ms = epoch_ms("2026-09-21T16:08:19Z")\n    event = {"city": "miami", "kwi_t": epoch_ms("2026-09-21T16:06:00Z"), "available_at_ms": signal_ms}\n    cycles = [\n        {"discovery_ms": signal_ms - 5000, "discovery": discovery("miami", [\n            evt("KXTEMPMIAH-26SEP2113", ["A", "B"]),\n            evt("KXTEMPMIAH-26SEP2114", ["D"]),\n        ])},\n        {"discovery_ms": signal_ms - 1000, "discovery": discovery("miami", [\n            evt("KXTEMPMIAH-26SEP2113", ["A", "B", "C"]),\n            evt("KXTEMPMIAH-26SEP2114", ["D"]),\n        ])},\n    ]\n    snap = m.matching_event_snapshot(cycles, "miami", event)\n    assert snap["event_ticker"] == "KXTEMPMIAH-26SEP2113"\n    assert snap["market_tickers"] == ["A", "B", "C"]\n    assert snap["event_target_at_ms"] == epoch_ms("2026-09-21T17:00:00Z")\n    assert snap["horizon_to_settlement_ms"] == epoch_ms("2026-09-21T17:00:00Z") - signal_ms\n\n\ndef test_past_target_and_post_signal_discovery_are_ignored():\n    signal_ms = epoch_ms("2026-09-21T17:00:05Z")\n    event = {"city": "miami", "kwi_t": epoch_ms("2026-09-21T16:59:00Z"), "available_at_ms": signal_ms}\n    cycles = [\n        {"discovery_ms": signal_ms - 1000, "discovery": discovery("miami", [\n            evt("KXTEMPMIAH-26SEP2113", ["PAST"]),\n        ])},\n        {"discovery_ms": signal_ms + 1000, "discovery": discovery("miami", [\n            evt("KXTEMPMIAH-26SEP2114", ["TOO_LATE"]),\n        ])},\n    ]\n    assert m.matching_event_snapshot(cycles, "miami", event) is None\n\n\ndef test_missing_future_event_fails_closed():\n    signal_ms = epoch_ms("2026-09-21T17:00:05Z")\n    event = {\n        "city": "miami",\n        "kwi_t": epoch_ms("2026-09-21T16:59:00Z"),\n        "available_at_ms": signal_ms,\n        "kind": "first_decision_eligible",\n    }\n    result = m.composite_result(event, None, [], window_ms=30000)\n    assert result["status"] == m.UNPROVEN_REACTION\n    assert "NO_PRE_SIGNAL_FUTURE_HOURLY_EVENT_DISCOVERY" in result["reasons"]\n    assert result["bucket_count"] == 0\n\n\nif __name__ == "__main__":\n    tests = [\n        test_ticker_hour_is_exact_eastern_market_time,\n        test_nearest_future_pre_signal_event_is_selected,\n        test_past_target_and_post_signal_discovery_are_ignored,\n        test_missing_future_event_fails_closed,\n    ]\n    for test in tests:\n        test()\n    print(f"E401_SYNC_LINKER_TESTS_PASS {len(tests)}")\n''', encoding="utf-8")

for path in (SRC, TEST):
    py_compile.compile(str(path), doraise=True)

test_run = run(sys.executable, str(TEST), timeout=60)
result["tests_pass"] = test_run.returncode == 0
result["test_stdout"] = test_run.stdout.strip()
if test_run.returncode != 0:
    result["status"] = "BLOCKED_TEST_FAILURE"
    result["test_stderr"] = test_run.stderr[-2000:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(12)

a17 = run(sys.executable, "control/jobs/run_e401_sync_a17.py", timeout=180)
try:
    a17_obj = json.loads(a17.stdout)
except Exception:
    a17_obj = {}
result["a17_pass"] = a17.returncode == 0 and a17_obj.get("status") == "PASS"
result["a17"] = {k: a17_obj.get(k) for k in [
    "status", "primary_events_total", "pending_primary_events_total",
    "evaluable_primary_events", "evaluable_cities",
    "valid_synchronized_capture_fraction", "unproven_primary_events",
    "reaction_observed_count", "no_reaction_observed_count",
    "minimum_evidence_met",
]}
if not result["a17_pass"]:
    result["status"] = "BLOCKED_A17_VALIDATION"
    result["a17_stderr"] = a17.stderr[-2000:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(13)

run("git", "add", str(SRC.relative_to(ROOT)), str(TEST.relative_to(ROOT)))
diff = run("git", "diff", "--cached", "--name-only").stdout.splitlines()
expected = {str(SRC.relative_to(ROOT)), str(TEST.relative_to(ROOT))}
if set(diff) != expected:
    run("git", "reset", "--", str(SRC.relative_to(ROOT)), str(TEST.relative_to(ROOT)))
    result["status"] = "BLOCKED_STAGED_SCOPE"
    result["staged_after_add"] = diff
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(14)

commit = run("git", "commit", "-m", "weather: link KWI signals to nearest future hourly market")
result["committed"] = commit.returncode == 0
if not result["committed"]:
    result["status"] = "BLOCKED_COMMIT"
    result["detail"] = commit.stderr[-1500:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(15)

push = run("git", "push", "origin", "main", timeout=180)
result["pushed"] = push.returncode == 0
result["status"] = "PASS" if result["pushed"] else "BLOCKED_PUSH"
if not result["pushed"]:
    result["detail"] = push.stderr[-1500:]
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result["pushed"] else 16)
