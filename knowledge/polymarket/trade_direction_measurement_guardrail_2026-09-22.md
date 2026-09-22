# Polymarket trade-direction measurement guardrail — 2026-09-22

Status: `RESEARCH_POSITIVE` measurement finding; economic status `NO_PROVEN_EDGE`.

## Observation
A 2026 Polymarket microstructure paper, *The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book* (Dubach), reports a continuous public WebSocket archive of roughly 30 billion events over 52 days joined to authoritative on-chain trade records. On its preregistered 600-market panel, trade direction inferred from the public order-book feed agreed with on-chain ground truth only about 59% of the time (panel mean 0.615, 95% CI 0.58–0.65). The paper further reports that effective-half-spread and Kyle-lambda signs frequently flip depending on feed-inferred versus on-chain trade direction.

Source: arXiv:2604.24366, public academic source, retrieved 2026-09-22.

## Research-OS interpretation
This is a measurement/provenance guardrail, not an edge. Polymarket informed-flow, adverse-selection, maker-markout, aggressor-side and microstructure studies must not treat direction inferred solely from public order-book changes as authoritative when on-chain `OrderFilled` direction can be joined point-in-time.

For `PM-NR-V2-CONVERT-001`, the finding does not alter the formal conversion semantics or candidate state. It does affect any later execution-realism validation that uses trade direction, fills or markouts around a candidate observation.

## Required handling
- Preserve raw public CLOB evidence and on-chain fill provenance separately.
- Source trade direction from on-chain `OrderFilled` events where the research question depends on aggressor side.
- Do not backfill unavailable point-in-time evidence into an earlier candidate observation.
- Do not infer market/execution edge from this measurement result.

## Red-team consequence
Failure pattern: `PUBLIC_FEED_INFERRED_TRADE_DIRECTION_AS_GROUND_TRUTH`.
Cheap kill: if a Polymarket flow/adverse-selection result materially depends on feed-inferred aggressor direction and lacks an authoritative fill join, mark that component measurement-blocked rather than economic evidence.

Economic conclusion: `NO_PROVEN_EDGE`.
