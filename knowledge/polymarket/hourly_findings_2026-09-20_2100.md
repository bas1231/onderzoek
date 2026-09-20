# Polymarket hourly findings — 2026-09-20 21:00 CEST

Status: RESEARCH_ONLY / NO_PROVEN_EDGE

## PM-NR-PUBLIC-MAP-003 — public metadata bridge is substantially better than prior blocker implied

Fresh public research changes the tooling picture for the NegRisk algebra lane.

1. Polymarket's public Gamma market records expose the identifiers needed to bridge metadata to executable books: `conditionId`, `questionID`, `clobTokenIds`, `negRisk`, and (for NegRisk records) `negRiskMarketID` / `negRiskRequestID`. Public Gamma examples also expose best bid/ask and fee schedule metadata, while the public CLOB API uses the returned token IDs for read-only price/orderbook queries.
2. A current independent Gamma client documenting the live 2026 schema additionally records event-level `negRiskFeeBips`, market-level `negRiskMarketID`, and for v2 markets `onchainEventId`. It documents `onchainEventId` as the parent v2 on-chain event id shared by every market in a NegRisk event, derived from the v2 condition ID with the condition index cleared. This is useful schema evidence but remains secondary until reproduced directly against live Gamma records.
3. Official NegRisk operator documentation confirms the on-chain semantic bridge: `prepareMarket(_feeBips, ...)` creates a market and `prepareQuestion(_marketId, ..., _requestId)` attaches questions; requestIds differ from questionIds. Therefore a permissionless/public census does not inherently require a paid indexer if Gamma supplies the market/event identifiers and public CLOB supplies books. On-chain event reconstruction remains valuable for independent verification/provenance rather than necessarily being the discovery source.

## Consequence

The previous blocker `no proven free end-to-end mapping` is narrowed. A zero-cost research path is now plausible:

`Gamma event/markets -> negRiskMarketID/onchainEventId + question/condition/token IDs + fee metadata -> public CLOB token books -> protocol cashflow model`.

This is **not yet a proven end-to-end census**, because this run did not enumerate a complete current active NegRisk event and independently reconcile every child market against on-chain `MarketPrepared/QuestionPrepared` events. `negRiskFeeBips` and `onchainEventId` should be treated as live-schema leads until directly sampled from current Gamma v2 records.

## Falsification / limits

- Gamma `bestBid`/`bestAsk` is discovery metadata, not execution proof; actual candidate evaluation still requires contemporaneous full CLOB depth per token.
- `conditionId` is not the NegRisk `marketId`; do not conflate identifiers.
- `questionID`, `negRiskRequestID`, and on-chain request/question IDs have distinct semantics.
- Event grouping in Gamma does not by itself prove the exact-one-TRUE invariant required by the conversion identity; rules/market semantics remain a separate proof gate.
- No price-positive instance was established, no gas/approval/inventory/depth calculation was performed, and no trading/wallet action occurred.

## Director disposition

KEEP RESEARCHING `PM-NR-V2-CONVERT-001`. The data-acquisition blocker has weakened enough to justify a read-only census/reconciliation experiment, but there is still no signal, market, or execution edge.

Economic status: `NO_PROVEN_EDGE`.
