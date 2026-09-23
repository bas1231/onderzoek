# Prediction Research-OS — 2026-09-23 17:10 CEST — bounded Recon priority

Status: `NO_PROVEN_EDGE`
Local runtime state: `LOCAL_RUNTIME_CONFIRMED_IDLE`
AI exchange: `CONFIRMED IDLE`

## Governor / exchange
`control/hourly/scheduled_worker_contract.json` was read first. Valid historical `PVA_AI_EXCHANGE_REQUEST_V1` traffic exists. The newest request directly checked for this bounded run was `hourly-20260923T140000+0200`, and it has a matching response with exact request SHA/token. Direct checks for 15:00, 16:00 and 17:00 request paths returned no request. Native bounded Recon therefore proceeded. No paid action, live trade/order, wallet/fund movement, credentials, post-close leakage, security misuse or OpenAI API use.

## Mandatory Recon priority — TASK-RECON-KALSHI-DOCS-001
Read `agents/roles/recon_scout.md` and `control/recon/KALSHI_EXHAUSTIVE_DOC_SWEEP_2026-09-23.json`. This run materially started the persistent exhaustive documentation sweep rather than merely acknowledging the task.

### Surface completed this run
Cluster: Kalshi event-contract `fees/rebates/incentives/rewards`.

Reviewed public Kalshi Help Center material for:
- Liquidity Incentive Program;
- Volume Incentive Program;
- Liquidity and Volume Incentive Programs: Where to Find Them;
- Fees;
- Limit Orders.

A durable coverage manifest was created at `knowledge/kalshi/recon/KALSHI_DOC_COVERAGE_2026-09-23.json`; the persistent task was moved from READY to IN_PROGRESS.

### Four-angle result
1. SEMANTIC/RULES: liquidity rewards are a separate conditional cashflow for qualifying resting liquidity and can accrue without fills; volume rewards require eligible executed CLOB volume. Neither is a guaranteed rebate. Program/market/participant conditions govern qualification.
2. TECHNICAL/IMPLEMENTATION: liquidity scoring uses random within-second order-book snapshots, dynamic Reference Price, Target Size and two-sided-depth qualification. Market-level incentive definitions are documented as exposed via the public Trade API, but exact endpoint/schema reconciliation remains a gap. UI qualification/earnings indicators are explicitly non-final.
3. ECONOMIC/EXECUTION: incentives can in principle offset fees/adverse-selection costs, so even cent-scale net EV remains research-eligible. No positive net EV is established: current market pool, competition, fill probability, adverse markouts, exact fees, inventory risk and participant eligibility are not jointly measured. Volume rewards are documented with a maximum reward of $0.005 per contract. For direct reward capture, documented non-US ineligibility is a present access blocker for an international user.
4. ADVERSARIAL/CHANGE/RESURRECTION: killers include non-US reward ineligibility, program modification/termination, two-sided-depth exclusions, minimum payout, competition dilution, maker fees, adverse selection and non-final UI estimates. Recheck triggers are changes to eligibility, reward periods/caps, Target Size/Discount Factor, API fields, fee overrides or material liquidity/competition.

Routing: `WATCH`, not `HUNT`. No candidate promotion or kill. Economic conclusion remains `NO_PROVEN_EDGE`.

### Remaining coverage gaps
General rulebook; product-specific settlement corpus; cancellation/void/no-data/fair-price/MOR; full REST schemas including direct incentive endpoint reconciliation; WebSocket sequencing/lifecycle; matching/queue/early-close; combo/MVE; data-source/revision/rounding corpus; changelog/deprecations; regulatory filing universe. Next bounded surface: public Trade API incentive schema + governing regulatory notices + fee-schedule reconciliation.

## Profitable-trader scouting
New discovery lead: public podcast metadata reports Kalshi trader Clay Alter/ClayA crossed roughly $1.5M profit in eight months while trading manually through the UI. Classification `CLAIM_ONLY` in this run: no independent account-history reproduction was completed. Mechanism is not yet sufficiently specified for CLONE_MUTATE. Separate public claims around top Kalshi traders remain discovery leads only. No copy trading.

## Weather / TWC / KWI
`GEEN NIEUWE UITKOMST`. No new post-cutoff preregistered full-station validation result was established. Preserve existing KWI gates.

## Control plane / candidates / negatives
No new bridge/executor/exchange incident established. Existing candidate states remain unchanged: Asset-Rank needs a proven full passive fill; KWI needs post-cutoff validation; Payoff Identity needs a concrete primary-rule state space, formal proof and synchronized executable L2. Negative evidence preserved; incentive documentation does not resurrect a falsified route by itself.

## Research Director
This run's durable progress is Recon coverage, not an economic survivor. The incentive cluster is now explicitly covered with provenance, four-angle analysis, gaps and WATCH triggers. Continue the exhaustive sweep on the next uncovered surface without repeating this cluster unless a material trigger fires.

Economic conclusion: `NO_PROVEN_EDGE`.
