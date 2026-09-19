# KXTEMPMIAH participation regime around verified KWI usage

Date: 2026-09-19  
Status: **OBSERVED / CAUSALITY_UNKNOWN / NO_PROVEN_EDGE**

## Claim
A secondary tick-data archive shows a large change in KXTEMPMIAH market microstructure during the second half of August 2026, near the period in which contract-specific Synoptic / Kalshi Weather Index settlement semantics can be independently verified.

This is **not** evidence that the KWI source change caused the participation change, and it is not evidence of an economic edge.

## Source anchors

Primary/regulatory:
- The CFTC product list shows the Miami Kalshi Weather Index product certified on 2026-08-12.

Contract-specific secondary mirror:
- A 2026-08-24 KXTEMPMIAH event mirror reproduces rules naming Synoptic Data and the Kalshi Weather Index Methodology.
- Earlier exact KXTEMPMIAH event rules have not yet been independently reconstructed in this research session, so 2026-08-24 must not be called the actual source-cutover date.

Market-data archive:
- CryptoStruct publishes day-level summary statistics derived from its recorded KXTEMPMIAH trades and L2 feed.

## Observed microstructure split

Using only the visible day rows 2026-08-15 through 2026-09-07 and treating 2026-08-24 as a **verified-KWI anchor, not a proven cutover**:

### Before 2026-08-24
9 visible days (2026-08-15 through 2026-08-23):
- mean turnover-weighted quoted spread: ~18.95 cents;
- median quoted spread: 17.1 cents;
- mean L2 updates/day: ~182k;
- median L2 updates/day: ~128k;
- mean trades/day: ~1,716;
- median trades/day: 1,566.

### From 2026-08-24 through 2026-09-07
15 visible days:
- mean turnover-weighted quoted spread: ~9.80 cents;
- median quoted spread: 9.15 cents;
- mean L2 updates/day: ~1.60 million;
- median L2 updates/day: ~1.40 million;
- mean trades/day: ~5,039;
- median trades/day: 5,431.

## Interpretation

The market clearly entered a much more competitive/high-activity regime around this period. Plausible explanations include, but are not limited to:
- KWI product/source changes;
- designated liquidity-provider participation;
- broader product rollout or UI promotion;
- API/bot adoption;
- seasonal/user-volume changes;
- archive/capture methodology changes.

No causal explanation has been proved.

## Research implication

KAL-WX-E001 must not pool early low-liquidity and later high-liquidity KXTEMPMIAH observations as if execution conditions were stationary.

At minimum, development analysis should retain:
- calendar date;
- rules/source regime;
- spread/depth/liquidity state;
- fee/incentive regime;
- configuration version;
- market activity regime.

Any apparent historical market edge concentrated in the early wide-spread/low-L2 regime should be considered non-generalizable until it survives later high-participation data and prospective shadow.

## Provenance

- CFTC Kalshi Weather Index product filings, accessed 2026-09-19.
- PMIP mirror for `KXTEMPMIAH-26AUG2408`, accessed 2026-09-19.
- CryptoStruct `KXTEMPMIAH` historical series summary, accessed 2026-09-19.

Economic status remains **NO_PROVEN_EDGE**.
