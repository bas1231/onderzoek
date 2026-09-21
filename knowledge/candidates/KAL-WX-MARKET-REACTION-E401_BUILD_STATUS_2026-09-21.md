# KAL-WX-MARKET-REACTION-E401 — build status — 2026-09-21

Status: **IMPLEMENTED / PROSPECTIVE MARKET EVIDENCE PENDING / NO_PROVEN_EDGE**

## Why this build exists

The external corroboration/competition note (`knowledge/kalshi/KALSHI_KWI_EXTERNAL_CORROBORATION_2026-09-21.md`) materially narrowed the KWI thesis. Broad early reconstruction of the Kalshi Weather Index is externally known and competitive. The next useful question is therefore not whether KWI can be predicted a few minutes early, but whether executable KXTEMP prices/depth still lag the **first decision-eligible** E390 signal long enough to survive realistic local latency.

E401 implements only that evidence gate. It does not place orders and does not infer profitability.

## Frozen signal definition

E401 reuses the existing E390 full-station incomplete-point eligibility rule without post-hoc modification:

- use local KWI manifest `retrieved_at` as availability timestamp;
- require numeric `latest_incomplete.t`;
- require the numeric incomplete station-temperature count to equal the previous complete point's `contributors`;
- require previous complete `t < target t`;
- require numeric previous complete `v`;
- primary signal value is the station mean;
- first qualifying snapshot is the primary `first_decision_eligible` event;
- changed same-target snapshots are revisions, not independent primary events.

## Implemented files

- `control/weather/market_reaction.py`
- `control/weather/test_market_reaction.py`
- `control/weather/kalshi_market_reaction_recorder.py`
- `control/weather/kalshi_market_reaction_ws.py`
- `control/weather/analyze_kwi_market_reaction.py`
- `knowledge/candidates/protocols/KAL-WX-MARKET-REACTION-E401.json`

## Evidence semantics

Primary evidence is continuous authenticated **read-only** WebSocket capture of `orderbook_delta` and public trades. REST capture exists only as a lower-resolution diagnostic baseline and must not support second-level repricing claims.

Reaction classification is deliberately conservative:

- `REACTION_OBSERVED`: first top-of-book/depth fingerprint change or public trade after signal;
- `NO_REACTION_OBSERVED_WITHIN_WINDOW`: no reaction with adequate complete capture coverage;
- `UNPROVEN_REACTION`: any relevant capture/timestamp/sequence ambiguity.

A reaction is an observed market event, not a causal claim that the KWI signal caused it.

## Fail-closed properties

The analyzer refuses favorable interpretation on:

- missing pre-event executable state;
- stale REST state;
- stale WebSocket transport coverage;
- capture gaps overlapping the event window;
- excessive REST cadence gaps;
- out-of-order observations;
- malformed book reconstruction;
- WebSocket sequence gaps;
- capture ending before the complete no-reaction window.

## Validation completed during build

The exact committed E401 core and unit-test blobs were synchronized to the locally validated bytes.

- core Git blob: `068c6340781dcc022b68ed8d9c7a19c57614d7b2`
- test Git blob: `0556d431a81ecf8b18e7b8edf95e654d4b59a1e6`
- unit tests: **13/13 PASS**
- Python compile check for core, tests, REST recorder, WebSocket recorder and analyzer: **PASS**
- synthetic end-to-end replay: **PASS**, known synthetic reaction recovered at 1000 ms
- static safety review: no order-submission / portfolio-order / wallet write path added

A separate Strix/local-executor validation task has also been queued; its future result is independent evidence and must not be assumed PASS until its RESULT.json exists.

## Pre-registered evidence threshold

Do not advance to E402 merely because the software works. E401 first requires:

- at least 30 evaluable primary city × target-minute events;
- at least 2 cities;
- at least 95% valid synchronized capture coverage.

## Next gate — only if E401 survives

`KAL-WX-ORDER-ARRIVAL-E402` should measure actual local signal-to-order-ready latency and compare its p95 with the E401 reaction-latency distribution.

Do **not** build queue/fill/maker execution logic as an economic strategy unless repeatable positive timing headroom survives that gate. If the executable market normally reacts before a realistic local order could arrive, the market-edge lane should be killed/downgraded rather than optimized post hoc.

## Guardrails

- live trading: **OFF**
- order submission/cancellation: **OFF**
- paid actions/data: **OFF**
- wallet/fund movement: **OFF**
- OpenAI API: **OFF**
- production credential material in logs/commits: **FORBIDDEN**

Economic conclusion: **NO_PROVEN_EDGE**.
