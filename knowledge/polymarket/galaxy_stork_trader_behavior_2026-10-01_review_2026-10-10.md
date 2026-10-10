# Galaxy/Stork Polymarket trader behavior — source review 2026-10-10
Status: RESEARCH_POSITIVE_DESCRIPTIVE / CLAIM_PARTIALLY_VERIFIED / NO_PROVEN_EDGE
Publication: 2026-10-01; discovered in this Research-OS run 2026-10-10 02:15 CEST.
Source: https://www.galaxy.com/insights/research/polymarket-trader-behavior-onchain-analysis-retail-profit-loss-specialization
Source class: original published research analysis of Stork-indexed public on-chain data, NOT independently reproduced; underlying query and immutable dataset not independently obtained.
Scope: Polymarket international exchange, NOT separate US venue. Full-history cohorts span different fee regimes.

## Observations explicitly reported by source
- ~3.07m wallets, 1.27bn matched orders and $82.8bn notional in full sample; filtered ~2.9m lower-frequency wallets.
- A >50 orders/active-day heuristic excludes 125,429 addresses (4.1% of accounts), representing 80.8% of orders and 41% of notional. This is an activity heuristic, NOT ground-truth bot detection.
- 69.2% of retained addresses had negative settlement-based P&L, reported aggregate -$338.9m. Excluded high-frequency addresses were reported +$246.8m; these totals do not net to zero because of unresolved/out-of-cohort positions.
- The report accounts for worthless expired positions even if not redeemed; wallet != person; multiwallet churn is unobservable.
- Topic concentration: 44.1% meet >60% of markets in one topic among >=5 categorized markets. Aggregate profitable proportion is 28.1% among these specialists versus 30.4% generalists, despite category differences: sports 25.1%, tech/science 41.2% (smaller sample), finance 36.8%. Generalists can fall into category through low activity.
- Retained account inactivity within 30 days: 15.2% after a loss versus 6.1% after a win; switching wallets can mimic churn.
- Report does not independently demonstrate a positive-EV trading rule; historical settlement P&L and present executable opportunity are distinct.

## Independent arithmetic / consistency
- 125,429 / 3,070,000 = 4.086%, consistent with rounded 4.1%.
- -338.9m + 246.8m = -92.1m, which the authors attribute largely to positions outside analyzed trader cohorts / unresolved positions; NOT an exchange-wide profit accounting identity.
- 28.1% - 30.4% = -2.3 percentage points: broad claim that specialization 'pays' is NOT supported unconditionally by aggregate specialist-v-generalist proportions.

## PRIMARY_SCOUT / RECON_SCOUT
PRIMARY: identify descriptive segmentation evidence and current fee-regime confounding; original public research is a new Git-memory lead, not a new October 10 publication.
RECON: reported profitability of high-frequency addresses is only a CLONE_MUTATE discovery lead; no identified replicable public strategy, no copy-trading or identity inference.

## SPECIALIST_DISPATCH MARKET_RESEARCH (behavioral/informed_flow)
Source/semantics: PASS for published definitions, INCONCLUSIVE for underlying independently verifiable computation.
Point-in-time/reproducibility: INCONCLUSIVE — no frozen underlying Stork query, public wallet sample, fee/reward/capital adjustments, or predeclared holdout reproduced in this run.
Economics/execution: INCONCLUSIVE — no contemporary market rules, executable L2, fill/queue, fees/rebates, market-impact or capital-lock proof.
Hypothesis (NOT fact): performance varies by domain and intensity after controlling for account age, turnover, fee epoch and sample selection. Cheapest decisive test is a small preregistered independent public wallet sample with settlement-including-worthless P&L, activity and topic cohorts; compare results under multiple automation thresholds. Do not use post-close information for decisions.

## RED_TEAM QUICK_KILL
- BOT_THRESHOLD_NOT_AUTOMATION_GROUND_TRUTH: >50 orders/active day is heuristic; high-frequency humans and low-frequency automation contaminate groups.
- WALLET_NOT_PERSON_AND_CHURN_NOT_IDENTIFIABLE: address reuse and migration confound behavioral inference.
- SPECIALIZATION_CONFOUNDED_BY_ACTIVITY_AND_TOPIC: specialist definitions and base rates differ; aggregate specialists underperform in report.
- HISTORICAL_SETTLEMENT_PNL_NOT_CURRENT_EXECUTABLE_EV: historical cohort P&L not a current order/fill strategy, and fee eras differ.
- HIGH_FREQUENCY_WINNERS_NOT_CLONEABLE: high-frequency profitability does not reveal legally accessible causal mechanism or prospective edge.
Retain prior negative evidence; no new candidate promotion/kill; no serious survivor; independent reproducer not warranted.

## Director / WATCH
Existing maker/tail-demand WATCH remains WATCH; new descriptive research does not meet a concrete changed decisive execution dependency. No automatic recheck/promotion. No active candidate state changes. Positive-EV small-profit admission policy unchanged.
Next: locate an independently reproducible, frozen public wallet cohort and reconstruct a small preregistered sample with explicit fee/reward/settlement accounting; only then test out-of-sample mechanism and executable market economics.
Economic conclusion: NO_PROVEN_EDGE.
Governor: research-only; no paid sources, live orders, wallet/funds, credentials, OpenAI API, post-close leakage, or strategy-code changes.
