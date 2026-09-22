# Kalshi U-3 threshold ↔ exact-value payoff pre-proof — 2026-09-22

Status: `SEMANTIC_PREPROOF / MECHANISM_PENDING`
Economic conclusion: `NO_PROVEN_EDGE`
Candidate: `PAYOFF-IDENTITY-MINING-V1`

## Goal

Test one concrete cashflow identity between Kalshi's September 2026 U-3 threshold ladder (`KXU3-26SEP`) and exact-value family (`KXECONSTATU3-26SEP`) **before inspecting synchronized prices or order books**.

This note is deliberately a pre-proof. It freezes the algebra and the semantic conditions that must be proven from primary Kalshi metadata. Failure of any condition blocks the identity.

## Publicly established facts

- Kalshi currently lists both September families concurrently: threshold outcomes such as `Above 4.0%` / `Above 4.1%` and exact outcomes such as `Exactly 4.1%`.
- Published threshold text for `KXU3-26SEP-T4.0` says the market resolves Yes if the **seasonally adjusted unemployment rate (U-3)** reported by the **Bureau of Labor Statistics in the Employment Situation Report** is **above 4.0% in September 2026**.
- Historical Kalshi exact-value pages show ordinary one-decimal outcomes such as July 2026 `Exactly 4.1% = Yes`.

These facts support the candidate shape, but are not enough to prove equivalence in every allowed settlement branch.

## Frozen candidate identity

Define the settlement variable `U` only if both contract families are proven to use the identical settlement value and exceptional-case policy.

Let:

- `A = YES(KXU3-26SEP-T4.0)` with ordinary-state payout `1[U > 4.0]`;
- `B = NO(KXU3-26SEP-T4.1)` with ordinary-state payout `1[U <= 4.1]`;
- `E = YES(KXECONSTATU3-26SEP-T4.1)` with ordinary-state payout `1[U = 4.1]`.

If `U` is restricted to the same one-decimal settlement grid for both series, then for every ordinary allowed state:

`A + B = 1 + E`.

State table around the only nontrivial region:

| U state | A: U>4.0 | B: U<=4.1 | A+B | E: U=4.1 | 1+E |
|---|---:|---:|---:|---:|---:|
| U <= 4.0 | 0 | 1 | 1 | 0 | 1 |
| U = 4.1 | 1 | 1 | 2 | 1 | 2 |
| U >= 4.2 | 1 | 0 | 1 | 0 | 1 |

So the proposed relation is **not** `A+B = E`; it contains a mandatory `$1` baseline cashflow/collateral component.

## Semantic conditions required for a real proof

All of the following must be established from primary Kalshi market metadata/rules for the exact September tickers:

1. identical underlying statistic: U.S. seasonally adjusted unemployment rate, U-3;
2. identical reference month: September 2026;
3. identical source/report: BLS Employment Situation;
4. identical value precision / rounding / settlement grid such that no allowed state exists strictly between 4.0 and 4.1 other than the exact 4.1 printed state;
5. exact contract `T4.1` truly means equality to the same settlement value, not a hidden interval/bucket transformation;
6. same treatment of first release vs later revisions;
7. same missing/delayed/cancelled-release branch;
8. same non-binary or exceptional settlement treatment, if any;
9. no differing early-close or determination rule capable of changing final cashflow semantics.

A single mismatch or unknown keeps `mechanism = PENDING/BLOCKED_SEMANTICS`.

## Evidence capture E451

A bounded local read-only capture job was added as `control/jobs/capture_kalshi_u3_semantics_e451.py` and dispatched as task `KALSHI-U3-SEMANTICS-E451`.

It requests only these public market objects:

- `KXU3-26SEP-T4.0`
- `KXU3-26SEP-T4.1`
- `KXECONSTATU3-26SEP-T4.1`

The artifact intentionally retains only rule/strike/time fields and drops bids, asks, volume, prices and order-book fields. This preserves the preregistered order: **semantics first, economics second**.

## Decision rule after E451

- If every semantic condition above is proven: record `MECHANISM_PASS` for this specific identity and only then preregister a synchronized executable-cost comparison including fees, collateral, depth, partial-fill/legging buffer and settlement timing.
- If any semantic branch differs: record the counterexample and reject this identity.
- If material fields remain absent/ambiguous: `BLOCKED_SEMANTICS`; do not infer equivalence from ordinary historical outcomes.

No price comparison, trading, paid data, wallet action or live execution is authorized by this pre-proof.

Economic conclusion remains `NO_PROVEN_EDGE`.
