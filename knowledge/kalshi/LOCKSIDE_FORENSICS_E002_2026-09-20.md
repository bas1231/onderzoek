# Lockside Forensics E002 — strategy reconstruction / comparable systems

Date: 2026-09-20
Status: RESEARCH ONLY — NO_PROVEN_EDGE
Campaign: LOCKSIDE-FORENSICS-001

## Purpose
Continue Lockside research without waiting for a user turn while the autonomous campaign control-plane build is pending. This record separates maker claims from independent comparable evidence.

## New primary/community evidence from maker thread

Source: Reddit post by u/Affectionate-Bowl-98, “Built an automated sports prediction market bot. 20 trades, 0 losses, 5.8% ROI in 10 hours.”

Observed public claims:
- Lockside was a dry run with fake money, using real market data; not live-money execution.
- Claimed strategy: buy YES at 92–99c when a team is winning by a “safe margin” in final minutes, then hold to settlement.
- Claimed total pipeline from score detection to order placement: ~500–600 ms.
- Claimed AWS ECS deployment in us-east-1 and sub-1ms latency to Kalshi API.
- Claimed average fill 81 contracts, range 1–217.
- Claimed projected win rate 95–97% and profitability threshold above 93%; this threshold remains inconsistent with the published average contract price/cashflow unless additional unreported mechanics materially change payoff accounting.
- Maker explicitly stated later that experiment used fake money and was stopped because hosting/upkeep was too expensive.
- Maker later reported about $100 of AWS credits consumed in ~1.5 weeks and said the experiment ended positive by only about $20.
- Maker said extreme-low-latency sports APIs were too expensive and that the system instead “piggyback[ed] on data/trades made by big sportsbooks”; he also referenced anti-toxic-orderbook validation because sportsbooks may emit fake orders. This is a material strategy/data-provenance clue but remains a community self-report, not verified implementation evidence.

Classification: CLAIMED unless independently reproduced/verified.

## Independent comparable public implementations

### shayd3/arbitrage-bot
Public GitHub project for live Kalshi sports markets.
- Polls ESPN public API and Kalshi.
- Late-game value strategy searches for implied probability lag relative to current game state.
- Supports NFL/NHL/MLB.
- Demonstrates that the broad “late-state sports + Kalshi repricing” mechanism is not unique to Lockside.

### stephencarvalho/kalshi-soccer-trading-bot
Public GitHub late-game soccer implementation.
- Current lead rules include 2+ goal lead and late 1-goal / tie conditions around minute 85.
- Uses capped YES prices and explicit red-card filters.
- Uses GTC limits and cancels resting orders when signal invalidates; partial-fill handling is explicit.
- This is useful evidence that a durable-state formulation (minutes, lead size, cards, price cap) is independently implementable without requiring sub-second score races.
- It is not evidence that the strategy is profitable.

### isaiahnick/ncaam-live-trader
Public GitHub NCAA Kalshi live-trading system.
- Uses a model probability vs executable ask framework and explicitly increases required edge late in the game.
- Public documentation warns that ESPN updates may lag the real game by 10–20 seconds and that stale prices can create phantom edges.
- It avoids the final ~4 minutes for new entries in its published framework because micro-state information dominates.
- This is important counterevidence to a simplistic “public score update -> guaranteed exploitable stale Kalshi quote” interpretation.

## Updated hypotheses

H-LS-1 Durable late-state premium: a sports state can remain high-probability for long enough that retail latency is not decisive. Still UNTESTED.

H-LS-2 Sub-second repricing race: profit depends on receiving a score/state update before Kalshi reprices. Lockside maker claims this but has not provided executable historical evidence. UNVERIFIED.

H-LS-3 Simulator fill optimism: fake-money fills may overstate capacity and ROI, especially when price/depth changes immediately after state updates. HIGH-PRIORITY falsification target.

H-LS-4 Alternative data source: maker may have derived fast state from big-sportsbook data/orderflow rather than ESPN alone. Exact source and legality/terms unknown. Treat as a data-provenance blocker, not as an actionable implementation path.

H-LS-5 Cost economics: infrastructure/data cost may materially exceed observed gross trading surplus at small scale. Maker’s later ~$100 / 1.5-week hosting statement versus ~$20 ending positive result makes this a serious economic kill condition.

## Research implications

1. Do not model Lockside as “ESPN-only” without proof.
2. Separate two mechanism classes:
   - durable late-state probability premium (seconds/minutes survive), and
   - event-update latency race (sub-second or few-second decay).
3. Historical simulation is insufficient unless fill logic can be reconstructed from contemporaneous L2/trades.
4. Public-source lag itself can create false apparent edge; source timestamp and receipt timestamp are proof obligations.
5. The broad mechanism has independent implementations, so novelty is low; evidence burden shifts to execution, calibration and cost.

## Next decisive work

- Reconstruct exact Lockside entry thresholds per sport if discoverable from maker comments/screenshots/code artifacts.
- Quantify break-even by price and current Kalshi fee regime.
- Search for archived landing-page/code artifacts and additional maker comments.
- Determine whether historical synchronized score + Kalshi L2 data exists for replay; otherwise specify a prospective shadow protocol.
- Compare latency sensitivity at 0.5/1/2/5/10/30/60s only with executable bid/ask/depth evidence.

Economic conclusion: NO_PROVEN_EDGE
