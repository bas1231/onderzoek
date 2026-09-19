# Public claims about what works + abuse/incident lessons — 2026-09-19

Status: **RESEARCH ONLY — NO_PROVEN_EDGE**

Doel: publiek bewijs scheiden van anekdote/marketing, en gedocumenteerde misuse-/incidentcases vertalen naar legale, overdraagbare researchmechanismen. Misbruikcases zijn **intelligence/negative-evidence**, geen operationele instructies.

## 1. Wat publiek het sterkst ondersteunt

### PUB-WORKS-001 — Maker/liquidity economics is materially different from taker economics

**Status:** RESEARCH_POSITIVE / venue-conditional

Evidence:
- Bürgi, Deng & Whelan (CESifo Working Paper 12122, 2026), >300k Kalshi contracts: low-price contracts underperform; high-price contracts small positive returns; maker/taker microstructure differs materially. Source: https://www.ifo.de/en/cesifo/publications/2026/working-paper/makers-and-takers-economics-kalshi-prediction-market
- Akey et al. (2026), Polymarket: profits are highly concentrated; public abstract reports successful traders disproportionately provide liquidity with limit orders, while unsuccessful traders disproportionately take liquidity. Source: https://doi.org/10.2139/ssrn.6443103
- Kalshi officially documents maker-side fee advantages/limit-order economics and liquidity incentive programs. Sources: https://help.kalshi.com/en/articles/13823811-limit-orders and https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program
- Polymarket officially documents liquidity rewards for competitive resting orders. Source: https://help.polymarket.com/en/articles/13364466-liquidity-rewards

Interpretation:
- `maker != edge`, but maker/taker state must be a first-class conditioning variable.
- Reward-adjusted economics can turn a marginal strategy into a different economic object.
- Adverse selection remains the core falsification target.

Required tests:
- same signal maker vs taker;
- 1s/5s/30s/5m markouts;
- queue/fill model;
- spread + fees + incentives + inventory;
- regime/category/time-to-close splits.

### PUB-WORKS-002 — Formal/combinatorial arbitrage has existed and has been exploited

**Status:** RESEARCH_POSITIVE historically; current execution edge unproven

Evidence:
- Saguillo et al., *Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets* (2025): heuristic semantic reduction + on-chain historical bid data identified single-market and combinatorial arbitrage; authors estimate about USD 40M realized extracted profit historically. Source: https://arxiv.org/abs/2508.03474
- Cheng, Yang & Zou, *Arbitrage Analysis in Polymarket NBA Markets* (2026): 75M+ L2 snapshots, only 7 single-market executable in-game episodes (median 3.6s); combinatorial opportunities more frequent but 76.9% were depth-constrained, average executable size ~14.8 shares. Source: https://arxiv.org/abs/2605.00864

Interpretation:
- Relation mining/algebra is a real mechanism class, not a theoretical curiosity.
- Easy/single-market arbitrage is heavily competed away.
- Search-space reduction + semantics + executable depth matter more than a naive scanner.
- Retail-scale opportunity can still be economically relevant at small capital, but must be measured live.

### PUB-WORKS-003 — Venue incentives/rewards are a genuine additive cashflow

**Status:** FACT_VERIFIED mechanism; edge depends on eligibility/competition/adverse selection

Evidence:
- Kalshi currently exposes liquidity and volume incentive programs via product and API; reward pools are market/time specific. Source: https://help.kalshi.com/en/articles/16076644-liquidity-and-volume-incentive-programs-where-to-find-them
- Kalshi liquidity rewards explicitly score resting orders; international/non-US users are documented as ineligible for that specific program as of 2026-09-19. Source: https://help.kalshi.com/en/articles/13823851-liquidity-incentive-program
- Polymarket documents daily Liquidity Rewards. Source: https://help.polymarket.com/en/articles/13364466-liquidity-rewards

Interpretation:
- Add `incentive_cashflow` as separate P&L component.
- Never infer strategy profitability from trading P&L alone when rewards/rebates are present.
- Eligibility and program version are point-in-time proof obligations.

### PUB-WORKS-004 — Good-faith market/rule bug discovery itself can be monetizable

**Status:** FACT_VERIFIED on Kalshi

Evidence:
- Kalshi Market Bug Bounty pays for privately reported market-rule/presentation/metadata bugs and ambiguities, with published tiers from USD 25 to USD 1,000+; attempting to exploit before reporting disqualifies the report. Source: https://help.kalshi.com/en/articles/13823852-market-bug-bounty-program

Interpretation:
- Add a separate **LEGAL_BOUNTY** lane to the red-team system.
- A rules contradiction can have two outputs: `TRADING_RESEARCH_BLOCKED/AMBIGUOUS` and `BOUNTY_CANDIDATE`.
- Private responsible reporting must occur before any exploitation attempt where bounty terms require it.

## 2. Public claims that are useful but NOT proof

### PUB-ANECDOTE-001 — Open-source sports MM/arbitrage bot with public-wallet P&L

Source: https://github.com/kachence/polymm

Author reports a retired Polymarket sports MM/arbitrage bot at roughly +USD 5k net, with +USD 8.3k arbitrage contribution offset by roughly -USD 3.2k directional/residual losses, and states profitability later decayed as speed/freshness became insufficient.

Classification: `ANECDOTAL_BUT_AUDITABLE`.

Lesson:
- hedge failure/residual inventory is where "guaranteed" arb can bleed;
- fresh fair-value source and execution speed can be the actual edge;
- public code after edge decay is not evidence the strategy still works.

### PUB-ANECDOTE-002 — Community reports repeatedly say execution dominates simple forecasting

Examples:
- 7-month Polymarket 5-minute crypto retrospective claims 1.7M candles + 4,600 windows; conclusion: book well calibrated, execution/split-merge/rebates/scale mattered more than prediction. Reddit: https://www.reddit.com/r/Polymarket/comments/1un85mg/
- Kalshi 40-experiment "graveyard" reports longshots, whale-following, taker favorites and simple momentum mostly failed under executable fills; maker execution did better in same signal tests. Reddit: https://www.reddit.com/r/Kalshi/comments/1vobcrl/

Classification: `ANECDOTAL`; use as hypothesis generator only.

## 3. Abuse / misuse / enforcement cases and transferable lessons

### ABUSE-001 — Trading on an outcome the trader can directly influence

Evidence:
- CFTC Feb. 25, 2026 advisory describes a political candidate who traded contracts on his own candidacy; Kalshi penalized and suspended the trader. Source: https://www.cftc.gov/PressRoom/PressReleases/9185-26

Classification: `ILLEGAL/PROHIBITED_EXECUTION`.

Transferable legal lesson:
- Add `OUTCOME_CONTROL_RISK` to venue/market integrity profile.
- Detect markets where a small identifiable actor or organization can materially control the settlement event.
- Such markets may exhibit unusual informed-flow/adverse-selection; use only as integrity/risk signal, never as instruction to trade using control over outcome.

### ABUSE-002 — Employment-based nonpublic information

Evidence:
- Same CFTC advisory describes a YouTube-channel editor who likely knew video contents before publication and traded related contracts; Kalshi imposed disgorgement, penalty and suspension. Source: https://www.cftc.gov/PressRoom/PressReleases/9185-26
- CFTC Aug. 28, 2026 order against Gabriel Perez: White House teleprompter operator used pre-delivery presidential speech information to trade mention markets, generating >USD 107.5k profit; disgorgement/penalty/trading ban. Source: https://www.cftc.gov/PressRoom/PressReleases/9289-26

Classification: `ILLEGAL/PROHIBITED_EXECUTION`.

Transferable legal lesson:
- Extreme apparently predictive flow may be informed flow rather than behavioral error.
- Build `INFORMED_FLOW_RISK` and treat sudden concentrated flow in information-sensitive markets as a veto/adverse-selection warning.
- Public first-decidability remains a distinct legal research lane only when information is genuinely public and point-in-time accessible.

### ABUSE-003 — Settlement-linked underlying manipulation risk

Evidence:
- Dai, Jia & Yu, *Settlement Manipulation in Prediction Markets* (2026) models and reports empirical settlement-time order-flow spikes/reversals around Polymarket 5-minute Bitcoin contracts; authors report manipulation largely absent in longer 15-minute contracts. Source: https://arxiv.org/abs/2606.31675

Classification: `MARKET_INTEGRITY_RISK`; no operational exploitation.

Transferable lesson:
- Add `SETTLEMENT_ENDOGENEITY` feature: can the prediction-market settlement variable itself be moved by trading the referenced underlying near settlement?
- Model settlement-window integrity and horizon as risk factors.
- Use to avoid adverse selection / flag venue design weaknesses, not to manipulate the underlying.

### ABUSE-004 — Oracle/adjudication can diverge from real-world event

Evidence:
- *Do prediction markets price events or adjudication? Evidence from disputed Polymarket markets* (Economics Letters, 2026): disputed-market prices in the settlement window forecast oracle adjudication rather than simply the underlying event; study reports audited-correct outcome overturned by oracle in ~3.4% of disputed markets. Source: https://www.sciencedirect.com/science/article/pii/S0165176526003721
- Polymarket arbitrage research also documents optimistic-oracle/dispute mechanics and notes complex cases can diverge from naive real-world truth. Source: https://arxiv.org/abs/2508.03474

Classification: `RESEARCH_POSITIVE` for black-box settlement modelling.

Transferable lesson:
- Predict **final contractual adjudication**, not objective truth.
- Add `event_state` and `adjudication_state` as separate nodes in the mechanism graph.
- Dispute/oracle state can create legitimate pricing differences but requires exact rules and point-in-time evidence.

### ABUSE-005 — Suspected coordinated/nonpublic-information clusters

Evidence:
- September 2026 reporting describes a cluster of interconnected Polymarket accounts with unusually successful bets on companies audited by KPMG; forensic analysts described an apparent unfair information advantage, but insider trading was not established in the cited public analysis. Source: WSJ/The Times reporting surfaced 2026-09-14.

Classification: `ALLEGATION/UNPROVEN`.

Transferable lesson:
- Never equate high win rate/large wallet with copyable alpha.
- Add wallet-cluster concentration and suspicious synchronization only as `INFORMED_FLOW_RISK`/research signal.
- No deanonymization or targeting of individuals.

## 4. New research lanes created from this review

1. **MECH-MAKER-ADVERSE-SELECTION** — maker/taker conditional edge with conservative queue/fills and markouts.
2. **MECH-INCENTIVE-OVERLAY** — spread/EV + rebates/rewards - adverse selection - inventory/capital cost.
3. **MECH-RELATION-MINING** — venue-agnostic formal dependency graph with executable depth proof.
4. **MECH-ADJUDICATION-BASIS** — market prices event-state vs final oracle/settlement adjudication.
5. **MECH-INFORMED-FLOW-VETO** — flow anomaly detector whose primary role is avoiding trades against likely informed flow.
6. **MECH-SETTLEMENT-ENDOGENEITY** — identify contracts where settlement source may be manipulable by activity in referenced underlying; research/avoidance only.
7. **LEGAL-BOUNTY-001** — automated rules/metadata contradiction scanner for sanctioned market-bug bounty programs.

## 5. Current synthesis

The strongest public evidence does **not** support "just forecast better" or "copy whales" as the default architecture. It supports a narrower picture:

- structural/formal arbitrage has existed but is competed, shallow and execution-sensitive;
- successful participants disproportionately appear on the liquidity-providing side, but maker adverse selection can erase spread/reward income;
- explicit venue incentives can be a meaningful P&L component;
- final adjudication can differ from naive event truth;
- suspiciously informed flow is often something to avoid, not imitate;
- rule/market bugs may be monetizable through sanctioned bounty programs without trading them.

Economic status remains `NO_PROVEN_EDGE`. These findings justify targeted cheap tests; they do not justify live strategy promotion.
