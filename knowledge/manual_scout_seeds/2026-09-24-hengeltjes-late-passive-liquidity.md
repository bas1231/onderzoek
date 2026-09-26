# MANUAL_SCOUT_SEED — Late passive liquidity “hengeltjes”

Date: 2026-09-24
Provenance: MANUAL_SCOUT_SEED supplied by user; do not attribute discovery to an autonomous scout.
Economic status: NO_PROVEN_EDGE.
Live trading: false.
Paid actions: false.
Wallet actions: false.

## Recovered original idea

The original hunting context was short-duration Kalshi weather markets, including “Where will it rain?” contracts. The practical idea was to avoid chasing near-certain contracts at unattractive 97–99¢ prices and instead leave very favorable passive limit orders much lower, roughly in the 85–90¢ area, waiting for an occasional seller/taker to hit them.

Most such resting orders would never fill and would therefore have zero shadow cost. The research question is whether the small subset that would have filled under strict, queue-realistic evidence wins often enough after settlement to have positive expected value.

The mechanism must not be inferred from forecast accuracy alone. The core conditional is:

P(win | an unusually favorable passive maker order would actually have filled)

and, after fees/friction:

EV = realized win probability - average executed price - fees/friction.

## Hard proof-of-mechanism example recovered from prior work

The confirmed profitable fill was not itself a rain contract. It was a Kalshi hourly-temperature contract in Miami:

- Market: Temperature in Miami at 5pm EDT
- Contract: 76°F or above
- Position: NO
- Visible NO price shortly before settlement: approximately 98–99¢
- Resting passive order: 5 NO @ 89¢
- The resting order unexpectedly filled completely around 22:58
- Maker fee: $0 in the observed trade context
- Cost: $4.45
- Final settlement: NO
- Payout: $5.00
- Realized profit: +$0.55
- ROI on deployed position: approximately +12.36%

This is proof that the fill mechanism can occur. It is not proof that the strategy has positive expected value.

## Candidate research question

Can we prospectively shadow many extremely favorable late passive orders across suitable short-duration Kalshi markets, especially the weather/rain market family that motivated the idea, and determine whether strict queue-realistic fills occur often enough and settle favorably often enough to create positive net EV?

The first AI should classify the mechanism and route it through the normal Research-OS without assuming in advance that the correct lane is weather, microstructure, informed flow, settlement, or another domain.

## Required falsification principles

- Queue position must be modeled conservatively; a trade at our price is not automatically our fill.
- Cancellations may not be counted as executed volume in PRIMARY results unless provenance proves queue depletion relevant to our simulated order.
- Partial fills count only for the quantity proven filled.
- Any sequence gap, reconnect ambiguity, restart ambiguity, or missing order-flow evidence must fail closed as UNPROVEN.
- Adverse selection is a primary kill test: favorable fills may occur precisely when a better-informed seller is dumping on us.
- Preserve post-fill markouts where possible.
- No hindsight in virtual order placement.
- Development/replay may debug mechanics, but fixed parameters must be frozen before prospective evaluation.
- If only optimistic fill assumptions are profitable, classify KILL/UNPROVEN.

## Safety / execution boundary

This seed authorizes research and read-only/shadow observation only. It does not authorize live order placement, cancel/amend, wallet or crypto actions, paid APIs, cloud/VPS spend, or any other cost-bearing action.
