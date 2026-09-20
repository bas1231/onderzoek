# Hourly findings — 2026-09-20 14:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## KAL-INCENTIVE-20260920-001 — incentive overlay is machine-discoverable, but user route is ineligible

**Source class:** official primary

Primary sources:
- Kalshi Help Center, Volume Incentive Program, published 2026-08-05: https://help.kalshi.com/en/articles/13823850-what-is-the-kalshi-volume-incentive-program
- Kalshi Help Center, Liquidity and Volume Incentive Programs, published 2026-07-26: https://help.kalshi.com/en/articles/16076644-liquidity-and-volume-incentive-programs-where-to-find-them
- Kalshi Help Center, Liquidity Incentive Program, current as retrieved 2026-09-20: https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program

### Verified facts

Kalshi exposes incentive-program definitions through its public Trade API, including market, reward type, dates, pool and liquidity parameters. Volume incentives can pay proportional rewards subject to a $0.005-per-contract cap; liquidity incentives score resting orders from randomized once-per-second order-book snapshots and depend on two-sided Target Size plus distance from a Reference Price.

### Important eligibility blocker

The official program pages state that international/non-U.S. users are ineligible for these rewards. Therefore this is a venue-mechanism fact and potential general research feature, **not an executable reward edge for the current Netherlands-based user route**.

### Research implication

The hourly factory should treat incentive state as a possible explanatory variable when studying market microstructure/adverse selection, because incentives can alter displayed depth, quoting behaviour and volume. It must not add expected reward income to the user's executable PnL unless eligibility is independently proven for the relevant account/jurisdiction and the exact program was active point-in-time.

### Pre-Build Killer

- novelty: useful new machine-readable overlay for the knowledge base;
- semantics: supported by official Kalshi documentation;
- economic headroom: unknown and competition-dependent;
- execution: user reward route blocked by stated international-user exclusion;
- decision: `KEEP_AS_MICROSTRUCTURE_FEATURE / EXECUTION_BLOCKED_FOR_USER_REWARD_CAPTURE`.

No strategy build warranted.

---

## KAL-COMBO-SCALAR-20260920-001 — combo payout is product-valued, not universally binary AND

**Source class:** official primary

Primary source:
- Kalshi Help Center, Combos, retrieved 2026-09-20 and marked updated today: https://help.kalshi.com/en/articles/13823820-combos

### Verified facts

Kalshi states that a combo is its own market, priced through RFQ, and its payout equals the product of underlying component settlement values. A component can settle to a scalar value between 0 and 1 (for example under a DNP/last-fair-price rule), and the combo payout then incorporates that scalar value rather than automatically becoming 0 or 1. The page gives an example of one component at 0.70 and two at 1.00 producing a 0.70 combo payout.

### Algebra/settlement implication

Any theorem/proof engine that models every combo as a pure Boolean conjunction is unsafe. Formal equivalence must preserve each leg's full settlement codomain and exception classes. For a candidate identity, `combo = product(leg settlement values)` is the safer primitive; reduction to Boolean AND requires proof that every included leg is binary under every allowed settlement branch.

### Chief Falsifier

1. **Semantics:** official current documentation directly supports scalar components.
2. **Data/execution:** no point-in-time executable RFQ quote was collected in this run, so there is no pricing or market-edge claim.
3. **Economics:** scalar semantics can destroy apparent locked-$1 floors or binary identities; fees, RFQ fillability and leg rules remain separate blockers.

Decision: `FACT_VERIFIED / ALGEBRA_GUARDRAIL`. This is a durable semantic constraint, not an edge.

---

## Director decision

No candidate crossed signal + market + execution gates. Economic status remains **NO_PROVEN_EDGE**.
