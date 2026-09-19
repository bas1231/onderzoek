# WS-DISTRIBUTION-001 — CFTC broadens passive-software access path

- observed_at: 2026-09-19T17:33:00+02:00
- source_class: PRIMARY_REGULATOR + SECONDARY_CONFIRMATION
- provenance: CFTC Press Release 9300-26 / Staff Letter 26-25, issued 2026-09-17; secondary confirmation PYMNTS 2026-09-17
- venues: US DCM ecosystem; directly relevant to Kalshi and future DCM prediction-market distribution
- mechanism_id: MECH-DISTRIBUTION-FRAGMENTATION
- status: FACT_VERIFIED / WEAK_SIGNAL (economic consequence untested)

## Finding
CFTC Market Participants Division made its earlier Phantom-specific passive-software no-action position broadly available to qualifying passive software providers. Subject to conditions, staff will not recommend enforcement for failure to register as an introducing broker/AP solely for providing and marketing software that facilitates user trading with registered FCMs, IBs and DCMs.

Primary: https://www.cftc.gov/PressRoom/PressReleases/9300-26
CFTC staff-letter index: https://www.cftc.gov/LawRegulation/CFTCStaffLetters/letters.htm
Secondary: https://www.pymnts.com/legal/2026/cftc-frees-non-custodial-software-developers-from-broker-rules/

## Why unexpected / potentially important
This is not an edge by itself. It lowers a regulatory distribution barrier for third-party wallets/apps/interfaces. If prediction contracts become accessible through more passive front ends, the same underlying DCM order book may receive heterogeneous cohorts with different information quality, latency, UX, order defaults and fee/rebate exposure. That can alter flow composition without creating a new venue.

## Relation to known research
- Extends `MECH-MAKER-ADVERSE-SELECTION`: more heterogeneous retail routing may change maker markouts and informed/uninformed-flow mix.
- Extends `MECH-INFORMED-FLOW-VETO`: interface/source cohort may become a useful conditioning variable if observable legally and publicly.
- Distinct from cross-venue arbitrage: this is **cross-interface / same-venue distribution fragmentation**.
- Does not override existing negative evidence against generic maker=edge or simple retail-fade claims.

## Transfer hypothesis
`new passive distribution channel -> changed participant/arrival mix -> measurable shifts in spread, queue competition, fill toxicity, market impact or category-specific calibration`.

No assumption that retail flow is systematically uninformed. The hypothesis fails if routed flow is economically indistinguishable after controlling for market/category/time.

## Required data
- point-in-time launch dates of third-party interfaces routing to each DCM;
- venue L2/trades before/after launches;
- if publicly exposed: order-source/interface metadata (do not infer private identities);
- spread, depth, cancellation, fill, 1s/5s/30s/5m markouts, time-to-close, category;
- fee/reward eligibility and versions.

## Falsification
Use event-study / matched-control design around a confirmed interface launch. Reject as useful mechanism if no persistent execution/microstructure difference survives market/category/time controls, or if source cohorts cannot be observed without private/nonpublic data.

## Execution blockers
No current evidence of an exploitable price effect; source attribution may be unavailable; distribution launches may coincide with marketing/product changes; adverse-selection direction is unknown.

## Weak-signal score (0-5)
- novelty: 4
- source_strength: 5
- mechanism_distance_from_known: 4
- plausible_economic_impact: 3
- transferability: 4
- time_sensitivity: 4
- testability: 3
- data_availability: 2
- legality: 5

## Urgency
WATCH. Build no trader. Add third-party interface launches/routing partnerships as point-in-time events to the research calendar and test only when sufficient public execution data exists.
