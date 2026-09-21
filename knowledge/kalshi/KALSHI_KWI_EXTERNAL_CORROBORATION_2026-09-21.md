# Kalshi Weather Index external corroboration / competition note — 2026-09-21

Status: **EXTERNAL_CORROBORATION / NOVELTY_WARNING / NO_PROVEN_EDGE**

## Why this note exists

The internal KWI lane (`KAL-WX-INDEX-001`, including `KWI-FULL-STATION-PRECANONICAL-V1`) has produced a research-positive prospective signal checkpoint. Before further build/promotion, the project must account for public evidence that other builders are independently reconstructing the Kalshi Weather Index before Kalshi publishes the canonical minute.

This note records external evidence only. It does **not** establish market edge, execution edge, or profitability.

## 1. Wethr.net independently exposes an early KWI reconstruction product

Public documentation for Wethr.net's **Hourly Index API (Kalshi Weather Index)** says that Wethr recomputes Kalshi's published Weather Index methodology from its own faster observation feed. Wethr states that its estimate is usually available **2–3 minutes before Kalshi publishes** the corresponding minute.

Source:
- https://www.wethr.net/edu/api-docs

Important semantics from the public documentation:
- Wethr labels the value as its own `estimate_f` / `estimate_c`, not as Kalshi data.
- Kalshi's canonical published value remains authoritative and can differ.
- The product is beta and can be wrong, late, stale or absent.
- Developer/Enterprise access is required for the documented Hourly Index API; this research project must not assume access or incur cost without explicit approval.

### Published accuracy evidence — useful but easy to overread

The same public documentation currently shows examples/accuracy summaries such as:
- 7d estimate-vs-official: `n=9732`, exact `99.41%`, MAE `0.001°F`.
- 30d estimate-vs-official: `n=14196`, exact `98.35%`, MAE `0.003°F`.
- 30d settlement rows: `n=239`, exact `97.49%`, MAE `0.007°F`.

However, Wethr explicitly describes the accuracy comparison as using its **final estimate for each minute as of Kalshi's t+5 publication deadline** versus the value Kalshi published. Therefore these public accuracy numbers do **not** by themselves prove that the *earliest* 2–3-minute-ahead estimate had the same accuracy, nor that a tradable market lag existed at first signal time.

Research implication: treat Wethr as strong independent corroboration that KWI is externally reconstructible and as evidence of active competition, **not** as proof of our executable edge.

## 2. Community tooling/archive exists around KWI and weather-market backtesting

Apify has a community-maintained `kalshi-weather-index` actor/dataset that exposes Kalshi minute index data, station observations, calibration information, `status` values including `incomplete`, and a public archive. Its page explicitly describes use for backtesting hourly KXTEMP strategies.

Source:
- https://apify.com/gratified_ashram/kalshi-weather-index

Research implication:
- KWI data collection and retrospective analysis are becoming commoditized.
- Novelty cannot rest on merely collecting the index or noticing that `incomplete` points exist.
- Our potentially distinctive mechanism is narrower: first decision-eligible incomplete snapshots that already contain the full expected numeric station set and their relation to the later canonical value.
- Any future novelty claim must be phrased at that narrower mechanism level and checked again before promotion.

The Apify product has paid usage tiers even though it also advertises a public archive. Do not make it a paid project dependency without explicit approval.

## 3. Synoptic timing supports the same latency scale but also adds robustness risk

Synoptic's current HF-ASOS documentation states that full one-minute HF-ASOS is a low-latency provisional real-time stream and, under normal operation, usually arrives with **2–5 minutes latency** from observation time.

Source:
- https://docs.synopticdata.com/services/high-frequency-asos

Synoptic also classifies HF-ASOS as **experimental** and warns that outages can occur.

Research implication:
- The external data path operates on the same few-minute scale as the internal KWI pre-canonical phenomenon.
- This makes a genuine information-timing mechanism plausible, but also makes the lane competitive and regime-sensitive.
- Robustness tests must include outages, degraded points, missing members, fallback behavior, configuration changes, and receipt/inclusion differences.

## 4. Relationship to internal E390 result

Internal E390 showed a strong prospective signal for the pre-registered full-station incomplete-point formulation. The external findings above increase confidence that early reconstruction of KWI is a real phenomenon in the ecosystem, but they do **not** independently validate the exact internal E390 eligibility rule or its implementation.

Do not merge the claims:
- **External Wethr claim:** reconstruct KWI from a faster independent observation feed, usually a few minutes before Kalshi publishes.
- **Internal E390 mechanism:** use a point-in-time Kalshi `incomplete` state when it already contains the full expected numeric station set to predict the later canonical value.

They are related but not identical.

## 5. New mandatory market-edge question

The decisive question is no longer merely whether the future canonical KWI can be predicted early. Public competitors appear able to do that too.

The decisive question is:

> At the **first decision-eligible timestamp** when our signal becomes available, does contemporaneous executable KXTEMP L2 still offer enough stale price/depth to produce positive net EV after fees, latency, depth walking, partial fills and adverse selection?

This must be evaluated from continuous authenticated WebSocket orderbook/trade evidence where possible. One REST snapshot per minute is insufficient for second-level repricing claims.

Required timing sequence per event:
1. local receipt time of the first decision-eligible signal;
2. exact signal value/probability and source/config provenance;
3. contemporaneous best bid/ask and full relevant depth;
4. orderbook deltas/trades after signal at sub-minute resolution;
5. hypothetical realistic order-arrival timestamp under actual network latency;
6. fillable price/size at that arrival timestamp;
7. price markouts and final settlement;
8. fees and all execution friction.

## 6. Additional falsification / kill rules

Add these to future KWI work:
- Do not infer tradable edge from prediction accuracy alone.
- Do not use Wethr's t+5 final-estimate accuracy as evidence for accuracy at the first early estimate timestamp.
- Kill the market-edge lane if executable KXTEMP prices already reflect the signal before a realistic order can arrive.
- Kill or downgrade novelty if public competitors expose the same narrow full-station incomplete-point mechanism before our next promotion gate.
- Treat premium/paid low-latency feeds as a separate infrastructure hypothesis; do not assume access and do not incur cost without explicit approval.
- Measure edge decay from first signal receipt, not from a later cleaner/final estimate.
- Preserve counterexamples during feed outages, degraded/quorum-edge states, inclusion flips and configuration/calibration changes.

## 7. Current conclusion

**Signal phenomenon: externally corroborated at the broader KWI-reconstruction level.**

**Novelty: reduced at the broad 'predict KWI a few minutes early' level; narrower internal incomplete/full-station rule may still be distinct but is not assumed novel.**

**Market edge: UNPROVEN.**

**Execution edge: UNPROVEN.**

**Economic status: NO_PROVEN_EDGE.**

The next build/research phase must prioritize synchronized market-reaction timing and executable depth rather than spending more effort merely proving that KWI can be reconstructed before canonical publication.
