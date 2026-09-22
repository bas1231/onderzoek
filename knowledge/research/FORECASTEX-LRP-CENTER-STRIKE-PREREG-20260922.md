# ForecastEx Financials LRP center-strike test — preregistration

Preregistered: 2026-09-22
Status: `BLOCKED_SEMANTICS / BLOCKED_PIT`
Economic conclusion: `NO_PROVEN_EDGE`
Live trading: `false`
Paid actions: `false`
Wallet actions: `false`

## Trigger

CFTC filing 63713 states that ForecastEx amended the Financials Liquidity Retainer Program to include a **center strike range** that pays a reduced incentive for quoting only the most liquid strikes in a market. The filing page reports `Certified` with date 2026-09-21.

Primary source:
- https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules/63713

ForecastEx also publishes public daily/intraday CSV data. Its Data page states that `Pairs` data is refreshed every 10 minutes.

Primary source:
- https://forecastex.com/data

## Research question

Does the certified center-strike incentive option measurably change the distribution of executable activity/liquidity across strikes in Financials markets?

This is a market-structure question, not an edge claim.

## Frozen hypothesis

`H-FEX-LRP-CENTER-001`

After the effective start of the certified Financials center-strike incentive regime, activity should become **more concentrated in the officially defined center-strike range relative to the same market's wing strikes**, compared with a point-in-time pre-regime baseline.

The causal story is deliberately weak: a lower reward for satisfying a narrower, high-liquidity quote set may alter where liquidity providers allocate quoting effort. The experiment tests the observable implication; it does not assume profitability or direction of spreads beyond the registered concentration hypothesis.

## Scope lock

The eligible Financials product universe and exact definition of `center strike range` MUST come from the official clean/redline Financials Liquidity Retainer Program exhibit associated with CFTC filing 63713.

Do not substitute a marketing-page product list. Do not add/remove products after seeing results.

If the official exhibit cannot be retrieved or does not define the center range sufficiently for deterministic classification, the experiment is `BLOCKED_SEMANTICS` and stops.

## Point-in-time regime boundary

Do not use `2026-09-21` mechanically as the treatment start merely because it is the certification date.

Before analysis, extract and freeze the actual effective date/time from the official filing/exhibit/notice. Data at or after that timestamp is `POST`; earlier data is `PRE`.

If effective timing cannot be established, stop with `BLOCKED_PIT`.

## Blocker observation — 2026-09-22

The current public CFTC filing metadata reliably establishes:
- filing 63713;
- the center-strike amendment description;
- receipt date 2026-09-04;
- certified status/date 2026-09-21;
- existence of an associated clean/redline Financials Liquidity Retainer Program exhibit.

However, through the currently available public retrieval paths in this research run, the associated clean/redline exhibit itself was not recoverable as a reliable primary artifact. ForecastEx Notices-to-Members search also did not surface a matching current notice containing the exact center-range definition or effective timestamp.

Therefore **no outcome data has been inspected for this hypothesis**. Per the preregistered rules, Stage A does not start.

Current blockers:
- `BLOCKED_SEMANTICS`: official center-strike range/product scope not yet recovered deterministically;
- `BLOCKED_PIT`: actual effective date/time not yet recovered from the primary exhibit/notice.

This is a clean methodological stop, not negative evidence against the economic hypothesis.

## Stage A — zero-cost public-data test

Use only ForecastEx public CSV data initially.

Required raw artifacts:
- immutable copy/hash of each source CSV;
- retrieval timestamp;
- source URL;
- product/market/strike identifiers;
- classification into center vs wing derived solely from the official exhibit;
- no post-hoc filtering based on observed outcome.

Primary metric:

`center_share = center_pair_count / all_pair_count`

computed per eligible market and fixed observation window.

Primary comparison:

`delta_center_share = POST center_share - PRE center_share`

Secondary descriptive metrics, only if fields exist in the public files:
- pair count per strike;
- notional/contracts paired per strike;
- fraction of strikes with any paired activity;
- center-vs-wing activity concentration ratio;
- time-of-day matched activity.

Do not invent unavailable fields. Public `Pairs` data is not L2 depth and must never be described as order-book liquidity.

## Baseline/window lock

Before reading outcome values:
1. determine the earliest complete POST window available after the actual effective timestamp;
2. use an equal-duration PRE window immediately preceding it;
3. match weekdays/time-of-day where possible;
4. exclude only documented exchange-wide maintenance intervals using a frozen rule;
5. preserve all zero-activity observations.

No selecting a prettier pre-period after viewing results.

## Stage A decision rule

The public-data stage is a **screen**, not proof of edge.

- `NO_EFFECT_SIGNAL`: center-share does not change consistently across the preregistered Financials universe -> PARK; do not build a live-market collector for this lane.
- `STRUCTURAL_CHANGE_SIGNAL`: center-share moves in the hypothesized direction across a broad enough share of the locked universe that a single product/outlier does not explain the aggregate -> permit Stage B research only.
- `MIXED/UNDERPOWERED`: preserve result and wait for more POST data; do not relax the test.

No p-value threshold is preregistered until the exact observation granularity/sample structure is known. Do not retrofit significance testing after inspecting results; if a formal statistical model is later used, preregister it separately first.

## Stage B — execution-realism test (conditional only)

Stage B is allowed only after `STRUCTURAL_CHANGE_SIGNAL` and a separate cost/access check.

Target observations:
- best bid/ask and sizes at center and wing strikes;
- synchronized timestamp;
- same-market cross-strike snapshot;
- executable fee path;
- stale-data indicator where available.

IBKR documents ordinary Event Contract market-data snapshots/streams for ForecastEx instruments. **Do not use the IBKR Regulatory Snapshot endpoint** unless the user separately approves its potential cost; IBKR states that regulatory snapshots can incur USD 0.01 per request unless covered by a subscription.

Standard authenticated market data also remains fail-closed on cost: before collection, prove that the account's existing access/subscription makes the planned requests non-chargeable. No assumption of free access is allowed.

No order entry, cancellation or trading is authorized.

## Economic gate

Even a confirmed center/wing liquidity redistribution is not an edge.

Promotion beyond `STRUCTURAL_CHANGE_SIGNAL` requires, separately:
- a falsifiable mechanism that produces mispricing or execution surplus for a Customer;
- simultaneous executable prices/sizes;
- all customer fees;
- slippage/partial-fill assumptions;
- capacity estimate;
- point-in-time replay or prospective shadow validation;
- Red Team survival;
- independent reproduction where required.

Default remains `NO_PROVEN_EDGE`.

## Kill conditions

Kill/PARK this lane if any of the following holds:
1. official center-strike definition cannot be recovered deterministically;
2. actual effective timestamp cannot be established;
3. public Pairs data cannot map trades/pairs to the locked center/wing classes;
4. no consistent concentration change appears after sufficient POST observations;
5. the apparent change predates the regime or is explained by a product-list/expiry change;
6. later executable-data collection would require unapproved cost;
7. any effect exists only after post-hoc product/window selection.

## Resurrection conditions

A BLOCKED/PARKED lane may be reopened only by new evidence that changes a named blocker: retrieval of the official clean/redline exhibit, a matching ForecastEx notice with deterministic center-range/effective timing, a longer untouched POST window after semantics are locked, a new free executable-data source, or a documented change in the incentive regime.
