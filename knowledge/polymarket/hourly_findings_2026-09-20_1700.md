# Polymarket hourly findings — 2026-09-20 17:00 CEST

Status: durable methodology / architecture finding; **not an economic edge**.

## Finding — NegRisk execution proofs must be versioned to current contracts

Primary-source review found a material architecture/versioning issue for the 16:00 NegRisk research lane.

Polymarket's current official Contracts page identifies the legacy `Neg Risk Adapter` at `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296` as **`CLOB v1, deprecated`**. The same current source of truth lists the active Neg Risk CTF Exchange plus a separate V2 `NegRiskCtfCollateralAdapter`, and also lists a newer Combos stack (`PositionManager`, `NegRiskModule`, `CombinatorialModule`, `Exchange`, `AutoRedeemer`).

At the same time, Polymarket's current Negative Risk concept page still describes conversion as a call to the `Neg Risk Adapter` and says one NO share can be atomically converted into YES shares for every other outcome. This creates documentation/version ambiguity: the economic identity may remain valid, but the exact executable transformation path cannot be inferred from the concept page or from legacy-adapter research alone.

The public `ctf-exchange-v2` source confirms that the current `NegRiskCtfCollateralAdapter` explicitly references a `LEGACY NegRisk adapter` internally. Therefore `deprecated` does not automatically mean that every underlying legacy primitive is unused; it means the execution graph must be proven against the current V2 call path and deployed addresses rather than assuming the old user-facing adapter path.

## Consequence for Market Algebra / Settlement

For Polymarket NegRisk candidates, require a **versioned execution proof** with at least:

1. current market/product type;
2. current exchange/module/adapter addresses from the official Contracts source of truth;
3. exact callable transformation path for that market type;
4. directionality of every transformation;
5. collateral type/wrapping path;
6. required inventory/approvals and capital lock;
7. current fees/gas/depth;
8. proof that the historical mechanism/paper applies to the current deployed path.

Historical evidence about the legacy NegRisk Adapter may establish a mechanism or prior behavior, but by itself is **not current execution evidence**.

## Falsification impact

This weakens the 16:00 lane as a current executable candidate. The arXiv result about one-way NegRisk conversion remains useful as historical/methodological evidence, but until the current V2 transformation graph is independently reconstructed, any current arbitrage claim based on that directionality is `VERSION_EXECUTION_UNPROVEN`.

No strategy build is justified by this finding.

## Sources

- Polymarket official Contracts page (retrieved 2026-09-20): https://docs.polymarket.com/resources/contracts
- Polymarket official Negative Risk concept page (retrieved 2026-09-20): https://docs.polymarket.com/concepts/negative-risk
- Polymarket official `ctf-exchange-v2` repository, `NegRiskCtfCollateralAdapter.sol` (retrieved 2026-09-20): https://github.com/Polymarket/ctf-exchange-v2/blob/main/src/adapters/NegRiskCtfCollateralAdapter.sol
- Polymarket legacy NegRisk adapter repository (retrieved 2026-09-20): https://github.com/Polymarket/neg-risk-ctf-adapter

## Decision

Methodology update only. `NO_PROVEN_EDGE`.
