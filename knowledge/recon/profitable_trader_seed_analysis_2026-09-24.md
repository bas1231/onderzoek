# Profitable-trader seed analysis — 2026-09-24

Status: `DISCOVERY_ANALYZED / NO_PROVEN_EDGE`
Task: `RECON-PROFITABLE-TRADER-SEEDS-E001`

## New verification lane
Fresh research established that Kalshi's own public profile pages can expose account-level profit, trade count, categories and sometimes volume/posts. Examples found today include public profiles with seven-figure displayed profit. This gives Recon a primary-source verification lane for trader claims when a claimed identity can be safely matched to an opted-in public Kalshi nickname. It does **not** reveal ROI, hold time, hidden/private accounts, counterfactual selection, execution quality, or prove that a described mechanism caused the P&L.

Primary-source examples:
- https://kalshi.com/ideas/profiles/established.tyrannosaurus — displayed profit +$1,607,002, 2,409 trades, Sports/Entertainment.
- https://kalshi.com/ideas/profiles/metromike — displayed profit +$1,287,857.
- https://kalshi.com/ideas/profiles/sailor82 — displayed profit +$201,960, 14,910 trades, Climate And Weather/Sports.

Discovery helper only: https://kalshiscan.com/search describes indexing opted-in Kalshi public profiles and explicitly notes that private profiles are absent. Use Kalshi itself as authority where possible.

## Seed 1 — Iabvek
Verification class: `PARTIALLY_VERIFIED`.
Source: https://news.kalshi.com/p/interview-kalshi-trader-iabvek-new-york-mayor-race
Observed: Kalshi's own interview records Iabvek agreeing that total Kalshi profit was near $1m. It also gives concrete examples: satellite-caucus composition, uncounted UC Merced ballots, election-specific model errors, collaboration/blind-spot review, and a major Romania loss.
Mechanism extraction: domain-specific information decomposition and residual-information search against sharp conventional wisdom; not a mechanical copy-trade rule.
Four-angle review:
1. Semantics/source: strong first-party interview provenance for the claim, but not an independently audited P&L statement.
2. Data/reproducibility: examples are retrospective and selected; no preregistered corpus or full decision history.
3. Economics/execution: no synchronized historical bid/ask, depth, fees, fill or capacity proof for the cited wins.
4. Transferability: potentially reproducible as a research process (baseline forecast + neglected public factor), but requires domain-specific evidence and anti-hindsight controls.
Decision: `WATCH / CLONE_MUTATE research process only`; no candidate promotion.
Next decisive test: preregister a future election/public-counting market family, freeze conventional baseline + named neglected-factor signals before price movement, then compare forecast delta with contemporaneous executable market prices and later outcomes.

## Seed 2 — TroyCuban / RFQ
Verification class: `CLAIM_ONLY`.
Source: public Risk Takers episode metadata/transcript mirrors, 2026-05-20, describing >$700k on Kalshi in 2026 and full-time RFQ specialization.
Observed: the public episode description says the edge in RFQs is not simply pricing and describes a traditional-finance background. Kalshi's public API documentation exposes RFQ/Quote models, confirming RFQ is a real venue mechanism, not proving Troy's P&L or mechanism.
Mechanism hypothesis: selective liquidity provision / risk transfer, quote selection, inventory/netting and adverse-selection control may matter more than raw fair-value prediction.
Four-angle review:
1. Semantics/source: RFQ mechanism exists; exact current eligibility/access/minimums/rules need primary-source lock.
2. Data/reproducibility: no public complete RFQ decision/fill corpus tied to Troy was found in this pass.
3. Economics/execution: fees, quote hit rate, adverse selection, inventory/capital and access remain unresolved.
4. Transferability: cannot assume retail/public API access reproduces a professional RFQ workflow.
Decision: `WATCH`; no copy trading, no promotion.
Next decisive test: primary-source RFQ rule/access/fee lock plus a free/public point-in-time RFQ observation path, then measure quoted-vs-filled-vs-post-fill markout economics without orders.

## Seed 3 — ~40 automated Kalshi experiments / graveyard
Verification class: `CLAIM_ONLY`.
Sources: Reddit post and Pondletter republication dated 2026-08-14.
Observed claimed failures: longshot buying, taking favorites at ask, whale following, BTC-alt lag/momentum, dip buying; claimed survivor uses the expensive/favorite side via resting maker bids and emphasizes queue priority. Poster explicitly reports backtest-to-live fill/regime failures.
Adjacent evidence: Turbine's 2026-09-21 report says only 102/4,904 BTC15m strategy variants were profitable under its stricter execution model and that profitability changed sharply with fees/liquidity/next-candle fills; still publisher evidence, not independent reproduction.
Four-angle review:
1. Semantics/source: community/self-published; no authoritative account linkage.
2. Data/reproducibility: exact survivor window intentionally withheld and reportedly retuned; severe adaptive-search/multiple-testing risk.
3. Economics/execution: maker queue position, fill selection, spread, fees/rewards and adverse-selection are decisive.
4. Transferability: generic `buy favorites` is already negative evidence; only preregistered subgroup/queue hypotheses deserve testing.
Decision: `WATCH`, linked to `TASK-FLB-001`; preserve failed mechanisms in Failure Memory.
Next decisive test: preregister price-bucket x category x maker/taker groups, freeze selection before untouched data, and evaluate real passive fills plus post-fill markouts and fees/rewards.

## Red-team synthesis
Do not infer `publicly profitable account -> disclosed mechanism caused profits`. Public-profile P&L can improve claim verification but creates survivorship/selection bias and does not identify strategy. For all three seeds, the missing bridge is causal/reproducible mechanism evidence plus execution reality.

## Director adjudication
All three seeds now have explicit first-pass analysis and durable evidence. None qualifies as `HUNT` or promotion. Highest information gain is: (1) RFQ primary-source access/mechanics lock, and (2) preregistered FLB/maker execution experiment. Iabvek-style election research remains a process template awaiting a future preregistered market instance.

Economic conclusion: `NO_PROVEN_EDGE`.
