# Polymarket platform-integrity / operational-risk WATCH — 2026-09-24

Status: `WATCH / NO_PROVEN_EDGE`

## Observation
Fresh public reporting in the Wall Street Journal (reported 2026-09-20; surfaced in the 2026-09-24 scheduled sweep) describes material fraud/compliance and account-security incidents around Polymarket's U.S. expansion, including attempted stolen-card abuse and a later account-takeover/security incident. Polymarket disputes or contextualizes parts of the reporting and says controls were strengthened.

Source: WSJ reporting surfaced via public web search; secondary reporting only for this record. No private data or security testing was used.

## Research implication
This is not a trading edge. It is a platform-integrity / operational-risk WATCH trigger. Historical or prospective strategy evaluation must not collapse `market EV` into `realizable user EV`: funding controls, account availability, withdrawal reliability, incident response, and jurisdiction/product access can invalidate otherwise positive paper economics.

For Polymarket-US or other newly expanded frontends, candidate-grade execution evidence should therefore preserve venue/product identity and point-in-time operational availability alongside price/depth/fees. A platform incident or fraud-control change can be a regime-change trigger for rechecking execution assumptions, but never auto-promotes a candidate.

## Edge separation
- Signal edge: not established.
- Market edge: not established.
- Execution edge: not established.
- Operational-risk relevance: established as WATCH only.

## Red-team guardrail
Reject the inference `platform weakness/security incident -> exploitable opportunity`. No operational security misuse, fraud, account abuse, credential use, or circumvention is permitted. Research is limited to lawful public consequences such as availability, fees, rules, liquidity, settlement, and execution reliability.

## Next decisive test
Only re-open economics when a concrete candidate depends on the affected venue/product/time window. Then verify contemporaneous official availability/rules plus executable depth, fees, funding/withdrawal constraints and incident status. Otherwise preserve as low-cost WATCH memory.

Economic conclusion: `NO_PROVEN_EDGE`.
