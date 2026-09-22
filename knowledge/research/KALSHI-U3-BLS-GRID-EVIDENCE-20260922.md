# Kalshi U-3 identity — primary BLS settlement-grid evidence

Date: 2026-09-22
Candidate: `PAYOFF-IDENTITY-MINING-V1`
Status: `SEMANTIC_SUPPORT / NOT_MECHANISM_PASS`
Economic conclusion: `NO_PROVEN_EDGE`

## Purpose

Resolve one preregistered semantic question for the September 2026 U-3 threshold ↔ exact-value identity without inspecting prices: does the **reported BLS U-3 value** live on a one-decimal published grid, so that there is no published Employment Situation state such as 4.05% between 4.0% and 4.1%?

## Primary BLS evidence

### U-3 is the official unemployment rate

BLS `Concepts and Definitions (CPS)` states that U-3 is the official unemployment rate and defines it as total unemployed divided by the civilian labor force times 100.

Source: https://www.bls.gov/cps/definitions.htm

### The Employment Situation publishes the U-3 rate at one decimal

Current BLS Employment Situation tables display U-3 values such as `4.1`, `4.3`, `4.4`, etc. BLS's 2026 statistical-significance factsheet makes the precision distinction explicit: it uses the published unemployment-rate values in the A tables (for example 4.3% and 4.4%) while separately saying that the significance tables calculate the over-the-month change **with more precision than appears on the A tables**, giving an unrounded change such as `0.12`.

Source: https://www.bls.gov/cps/factsheets/statistical-significance-unemployment-rate-change-over-time.htm

BLS also explicitly described the publication convention in its seasonally-adjusted-series documentation: unemployment rates are **"rounded to one decimal place as published"**, while effects become more visible if rates are computed to more decimal places.

Source: https://www.bls.gov/cps/cpsrs2002.pdf

## Consequence for the frozen payoff identity

If the three Kalshi September contracts all settle on the **same U-3 value as reported in the Employment Situation**, then the settlement value relevant to those contracts is published on a 0.1-percentage-point grid.

Under that condition, there is no published reported state strictly between `4.0` and `4.1`. Therefore the ordinary-state algebra

`YES(U > 4.0) + NO(U > 4.1) = 1 + YES(U = 4.1)`

is not defeated by a hypothetical published `U = 4.05` branch.

## What this does NOT prove

This evidence does **not** yet prove that all three Kalshi contracts use precisely the same published figure and exceptional branches. The following preregistered gates remain unresolved until exact contract metadata/rules are captured and reviewed:

- exact-value market really means equality to the same reported U-3 value rather than a hidden interval/bucket;
- threshold and exact families use identical reference month and source/report;
- identical first-release versus later-revision treatment;
- identical delayed/missing/cancelled-release treatment;
- identical exceptional/non-binary determination rules;
- identical early-close/finality semantics.

Therefore this note upgrades only the **reported-value precision/grid sub-question** to `SUPPORTED`, conditional on the contract rule referring to the reported Employment Situation value. It does not upgrade `mechanism` as a whole.

No price, order-book, volume, fee, trade, wallet or paid action was used.

Economic conclusion remains `NO_PROVEN_EDGE`.
