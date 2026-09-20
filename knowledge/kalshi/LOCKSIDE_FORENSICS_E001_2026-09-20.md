# LOCKSIDE-FORENSICS-E001 — source and claim reconstruction

Date: 2026-09-20
Status: **HYPOTHESIS_UNTESTED / NO_PROVEN_EDGE**
Venue: Kalshi
Source class: primarily COMMUNITY, cross-checked against PRIMARY Kalshi documentation
Search family: `live_sports_late_state / public-score-confirmation / external-sharp-feed-lag`
Branch note: research-only record; no strategy build, no orders, no paid data, no wallet actions.

## Research question

Can the publicly described Lockside late-game sports method be reconstructed well enough to test whether any economic surplus came from (a) genuinely underpriced late-game win probability, (b) latency / market-repricing lag, (c) execution / liquidity selection, or (d) small-sample / simulation artefact — and would any surviving effect plausibly remain executable on retail Strix/Starlink infrastructure?

Economic default remains `NO_PROVEN_EDGE`.

## Primary community source

Reddit post by `u/Affectionate-Bowl-98` in r/ClaudeCode, title: **“Built an automated sports prediction market bot. 20 trades, 0 losses, 5.8% ROI in 10 hours”**. Public post dated 2026-04-05; later comments extend into May 2026.

URL: https://www.reddit.com/r/ClaudeCode/comments/1scxr78/built_an_automated_sports_prediction_market_bot/

The linked CloudFront landing page is no longer fetchable from the current public URL. The codebase was not located in the first public-source sweep. Therefore dashboard data, trade rows and implementation details are not independently verified in E001.

## Claim matrix

| ID | Claim | Source status | E001 classification | Notes |
|---|---|---|---|---|
| LS-C001 | Strategy buys YES at 92–99c when a team is ahead by a “safe margin” late in the game and holds to settlement. | Creator self-report | CLAIMED | Exact sport-specific trigger rules mostly missing. |
| LS-C002 | Day-1 dry run: 20 trades, 20 wins, $1,522.52 deployed, $88.48 profit, 5.81% ROI, average buy price 95.1c, 9.7h window. | Creator self-report | CLAIMED | Explicitly paper/simulated, not live-money execution. |
| LS-C003 | Sport breakdown included NHL 6, NCAAM 1, MLS 2, NBA 3, MLB 1 in the visible table. | Creator self-report | CLAIMED | Visible sport counts sum to 13, not 20; seven trades are not explained by the visible breakdown. This may be omitted rows, formatting loss or inconsistent reporting. Needs original dashboard/trade tape. |
| LS-C004 | NHL trigger example: 2+ goal lead in final 5 minutes. | Creator self-report | CLAIMED | Most concrete sport-state rule found so far. |
| LS-C005 | Risk controls: loss-streak circuit breaker, score retraction detection, anti-toxic orderbook validation, slippage control, exposure caps, stale-game filter, half-Kelly with time decay. | Creator self-report | CLAIMED | Nine controls claimed, but only a subset are enumerated in prose. |
| LS-C006 | Stack: Python/FastAPI/SQLAlchemy, AWS ECS, Next.js dashboard, Kalshi WebSocket, Telegram. | Creator self-report | CLAIMED | Plausible but not independently verified. |
| LS-C007 | “Co-located in us-east-1 — sub-1ms to Kalshi API.” | Creator self-report | CLAIMED | Endpoint RTT is not equivalent to order-accept/fill latency. No measurement method supplied. |
| LS-C008 | Score detection → order placement pipeline ≈500–600ms and “way before price movement” on Kalshi. | Creator self-report | CLAIMED | No raw timestamps / decay curve / fill timestamps provided. |
| LS-C009 | Average fill ≈81 contracts, range 1 to 217. | Creator self-report | CLAIMED | Suggests liquidity mattered materially; fill simulation method unknown. |
| LS-C010 | ESPN score confirmation makes actual win rate exceed implied probability. | Creator self-report / inference | HYPOTHESIS_UNTESTED | Public score confirmation is not automatically market edge; contemporaneous market may already price it. |
| LS-C011 | “Win rate has to stay above 93% to remain profitable”; projected 95–97%. | Creator self-report | ARITHMETICALLY_SUSPECT | At reported 95.1c average buy price, no-fee break-even is ~95.1%, not 93%. Fees raise it further. Even using aggregate cash figures implies ~94.51% weighted effective cost before any unreported extra costs. |
| LS-C012 | Experiment later “went quite well” but ended with only about $20 positive result. | Creator self-report | CLAIMED | No final trade count, stake, fee treatment or time window supplied. |
| LS-C013 | Hosting consumed about $100 of AWS credits in ~1.5 weeks, leading creator to stop. | Creator self-report | CLAIMED | This makes infra cost economically material at the observed paper-P&L scale. |
| LS-C014 | Creator piggybacked on “data/trades made by big sportsbooks” because extreme-low-latency sports APIs were too expensive. | Creator self-report | CLAIMED / AMBIGUOUS | Exact provider, data semantics, timestamps and legality/ToS route unknown. Do not operationalize until clarified. |
| LS-C015 | “Anti-toxic orderbook validation” was needed because sportsbooks sometimes create fake orders. | Creator self-report | CLAIMED / AMBIGUOUS | No source or reproducible evidence supplied. Treat as unverified explanatory claim, not fact. |

## Immediate arithmetic audit

### Reported day-1 totals imply 1,611 winning contracts if profit is simply settlement payout minus deployed cash

If all 20 paper trades won and there was no exit before settlement:

`contracts ≈ deployed + profit = 1522.52 + 88.48 = 1611.00`

That is consistent with the claimed average fill of ~81 contracts (`1611 / 20 = 80.55`).

The contract-weighted effective cash cost implied by those totals is:

`1522.52 / 1611 = 0.94508` (~94.51c)

This does **not** necessarily contradict the stated “average buy price 95.1c”, because 95.1c may be an unweighted average of trade-level prices while the dollar totals are quantity-weighted. It does show that the exact trade tape is required before reproducing ROI.

### 93% break-even claim does not fit the described buy-and-hold structure

For a binary contract bought at cost `c` and held to a $1/$0 settlement, before fees:

`EV = q - c`

so break-even win probability is `q = c`.

Therefore:

- at 95.1c average purchase price, break-even is ~95.1% before fees;
- at the aggregate effective 94.51c cash cost implied by the reported totals, break-even is ~94.51% before any additional costs;
- current Kalshi taker fees near 95c add roughly 0.33c per contract for a 100-contract fill under the published quadratic schedule, pushing break-even upward, not downward.

Thus the creator’s statement that >93% wins is enough is not supported by the visible numbers unless some omitted feature changes the cashflow (for example price exits, rebates, or a different accounting definition). E001 found no such omitted feature.

## Small-sample warning

Twenty wins out of twenty does not establish a >95% true win probability. A streak of 20/20 still occurs with probability:

- ~23.4% if the true win probability is 93%;
- ~35.8% if true win probability is 95%;
- ~54.4% if true win probability is 97%.

So the observed perfect streak is compatible with a wide range of underlying probabilities and cannot by itself show positive expectancy at 94–96c entry prices.

## Primary-source Kalshi checks relevant to Lockside

1. Kalshi states that trading may remain open while it waits for an official source to confirm the result; a market remaining open is not evidence that the payout criteria are undecided. This supports studying late-state trading, but also means sport-specific settlement/finality rules must be checked for each series.
2. Kalshi’s current fee schedule uses a quadratic taker fee, with no settlement fee. Around 95c, the general taker fee is economically small but non-zero; on thin 4–8c gross margins it must be included.
3. Kalshi’s rules/help pages stress that each market’s source, close condition and determination criteria govern settlement. A scoreboard state is not automatically final settlement proof.

Primary references:
- https://help.kalshi.com/en/articles/13823821-market-faqs
- https://help.kalshi.com/en/articles/13823822-market-rules
- https://help.kalshi.com/en/articles/13823826-market-outcomes
- https://kalshi.com/docs/kalshi-fee-schedule.pdf

## Comparable public case found

A separate August 2026 r/algobetting post describes a local Kalshi sports bot using de-vigged Pinnacle odds as an external reference. It reports ~32ms local calculation, ~125ms receipt-to-decision, and ~538ms median / 1.2s p95 source-to-decision. The author frames the unresolved question correctly: whether the Kalshi price discrepancy survives through submission and fill. This is not independent proof that Lockside worked; it is useful prior art for the latency-decay experiment design.

URL: https://www.reddit.com/r/algobetting/comments/1vmjbkb/live_betting_bot_timing_and_execution/

## Pre-registered decomposition hypotheses

These are alternatives, not assumptions:

### LS-H1 — Late-state probability surplus
At specific score/time states, true conditional win probability is systematically higher than the executable Kalshi YES ask plus fees.

### LS-H2 — Repricing-lag surplus
The external sports signal updates before Kalshi and the executable surplus decays over seconds. Profitability depends strongly on end-to-end latency.

### LS-H3 — Liquidity-selection artefact
The apparent edge comes from assuming fills at displayed prices/depth that would not have been executable after source-to-order latency and queue competition.

### LS-H4 — Small-sample / selection artefact
The 20/20 day and later “positive” result are consistent with ordinary variance, omitted losing episodes, adaptive thresholds, or dashboard/accounting definitions.

### LS-H5 — Infra-cost domination
Even if per-trade paper EV is positive, data+AWS+maintenance cost overwhelms absolute expected profit at realistic retail capacity.

### LS-H6 — Sport-specific heterogeneity
Any effect is concentrated in particular sports/states (e.g. NHL 2+ goals / <=5m) and does not transfer to NBA/MLB/MLS/NCAAM.

### LS-H7 — Public-state already priced
ESPN/scoreboard confirmation adds no incremental information after conditioning on the contemporaneous executable Kalshi book; the apparent ‘confirmation’ is merely redundant signal.

## Kill gates before any strategy build

1. **Exact-rule gate:** recover or define immutable sport-specific triggers without tuning them on outcomes.
2. **Settlement gate:** prove sport/series close/finality semantics; scoreboard state alone is insufficient.
3. **Fee/accounting gate:** reconstruct historical fee schedule and whether claimed P&L included fees.
4. **Fill gate:** obtain contemporaneous orderbook/depth and define realistic taker/maker fill assumptions.
5. **Latency gate:** measure edge decay at 0.5s / 1s / 2s / 5s / 10s / 30s / 60s; if economic surplus dies before retail latency, classify as execution-blocked for Strix/Starlink.
6. **Independence gate:** cluster repeated trades by game/event; no treating multiple same-game episodes as independent.
7. **Out-of-sample gate:** thresholds learned from public examples cannot be validation. New untouched games are required.
8. **Materiality gate:** expected absolute profit after fees, slippage, loss tails and infra/data cost must be large enough to matter.

No strategy code is warranted yet.

## Required next evidence

- Original Lockside landing-page/dashboard archive or screenshots with trade rows.
- Exact 20 day-1 trade timestamps, tickers, side, state, quantity, quoted price, assumed fill price and fee accounting.
- Exact sport-specific “safe margin / final minutes” thresholds and whether they changed during the experiment.
- Exact external data source(s), source timestamps, receipt timestamps and score-retraction logic.
- Historical point-in-time Kalshi L2/trades around those events if recoverable.
- Historical April 2026 fee schedule / series fee-type.
- Final experiment trade count and complete P&L, not only the later “about $20 positive” statement.
- Any public copy of the codebase or independent reproduction.

## E001 verdict

`SOURCE_RECONSTRUCTION_PARTIAL`

The public creator post is useful enough to define a falsifiable research lane, but it is **not evidence of a proven profitable strategy**. The strongest immediate red flags are: simulated rather than live-money execution; only 20 reported day-1 trades; incomplete sport-count table; unknown fill simulation; no explicit fee treatment; missing exact thresholds; and the creator’s stated 93% break-even threshold conflicting with the visible contract economics.

Economic status: **NO_PROVEN_EDGE**.
