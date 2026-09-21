# KWI market reaction E401

Status: **research instrumentation only / NO_PROVEN_EDGE**.

`KAL-WX-MARKET-REACTION-E401` measures whether executable KXTEMP market state changes after the first decision-eligible KWI full-station incomplete signal defined by the E390 lane. It does not place orders and cannot promote the project to live trading by itself.

## Components

- `control/weather/kwi_market_reaction_e401.py` — deterministic signal extraction, order-book reconstruction and fail-closed reaction classification.
- `control/jobs/analyze_kwi_market_reaction_e401.py` — offline analyzer for already captured evidence.
- `experiments/prebuild/KAL-WX-MARKET-REACTION-E401.yaml` — preregistered timing and kill rules.
- `tests/test_kwi_market_reaction_e401.py` — synthetic deterministic coverage for direct/delayed/no reaction plus ambiguity failures.

## Evidence policy

Primary second-level claims require continuous authenticated read-only WebSocket capture with initial snapshot, contiguous orderbook deltas, trades, local receive timestamps and explicit reconnect/gap records. REST snapshots are only a coarse fallback and must not be used to claim sub-minute repricing latency when the capture cadence cannot support it.

Any missing recent pre-signal state, capture gap, out-of-order state, sequence gap, or capture ending before the full no-reaction window yields `UNPROVEN_REACTION` rather than a favorable inference.

## Safety boundary

This layer has no order-placement function, no portfolio mutation, no wallet action and no paid dependency. A later live or cost-bearing step requires separate explicit authorization.
