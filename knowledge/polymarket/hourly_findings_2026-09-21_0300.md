# Hourly finding — Polymarket finality/redemption — 2026-09-21 03:00 CEST

Status: durable methodology/negative evidence; **NO_PROVEN_EDGE**.

## New public evidence
Nechepurenko, *Resolution Is Not Settlement, Part I* (arXiv:2609.15368, 2026-09-14) reconstructs Polymarket Oracle request generations and shows that request creation, proposal, dispute/reset, Oracle finality and adapter terminality are distinct lifecycle states. The frozen population contains 185,550 adapter-question instances; exact extraction reports 504,332 Oracle lifecycle events. Exact stable-ID metadata linkage recovers 104,032/185,550 questions, leaving 81,518 unmatched. The paper explicitly does not substitute mechanism timestamps for external-source publication or contractual decidability clocks.

Nechepurenko, *Resolution Is Not Settlement, Part II* (arXiv:2609.15373, 2026-09-14) reconstructs CTF protocol finality and observed redemption. The exact bridge contains 108,638 linked conditions; 99,283 have observed protocol resolution at the fixed snapshot. Among resolved exact-linked conditions, 92,158 have any observed redemption and 91,817 positive-payout redemption. Median condition-specific time from first protocol resolution to first redemption is reported as 182 seconds (200 seconds for positive-payout redemption). The payout taxonomy includes 410 fifty-fifty vectors and two other valid non-canonical vectors in addition to canonical binary vectors.

## Factory interpretation
This is new relative to current Git memory searches for the paper titles/PayoutRedemption. It strengthens the settlement specialist's state-machine requirement:

1. external evidence / contractual decidability;
2. Oracle request generation and adjudication;
3. adapter terminality;
4. CTF ConditionResolution / protocol payout vector;
5. holder redemption / realized collateral.

These states are not interchangeable. `resolved`, `oracle final`, `redeemable`, and `redeemed` must never be collapsed into one timestamp/state in replay or execution claims.

## Negative evidence / falsification
- Observed redemption delay is **not** automatically an exploitable carry/latency edge. Redemption is holder action and does not itself identify entitlement or opportunity cost without a balance-consistent denominator and execution/capital model.
- Oracle finality does not prove protocol finality.
- Protocol finality does not prove holder realization.
- A redemption event alone does not measure what fraction of entitlement was redeemed.
- Non-canonical payout vectors mean a binary-only settlement parser can be wrong even when the market UI appears binary.
- Part I's incomplete metadata linkage is a hard warning against backfilling missing semantic identity from current metadata.

## Candidate impact
`PM-NR-V2-CONVERT-001` remains active but is not promoted. Its formal settlement verifier should eventually require the actual protocol payout vector/state and must not infer settlement solely from Oracle/adapter status. No current synchronized books, fees, gas, inventory or positive worst-case cashflow were produced by these papers.

## Agent routing
- scout: new papers discovered and deduplicated against Git.
- settlement: material new state-separation evidence.
- algebra: payout-vector taxonomy is relevant to proof semantics; no new executable identity proven.
- microstructure: 182/200-second redemption medians are descriptive, not an execution edge.
- behavioral/informed_flow/weather_twc: no new result.
- prebuild_killer: no build warrant.
- chief_falsifier: rejects any strategy based only on resolution-to-redemption timing.
- independent_reproducer: not warranted absent a positive economic instance.

Decision: **NO_PROVEN_EDGE**.
