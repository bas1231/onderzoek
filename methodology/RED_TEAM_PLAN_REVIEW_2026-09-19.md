# Red-Team Plan Review — 2026-09-19

Status: **ARCHITECTURE REVIEW COMPLETE — NO_PROVEN_EDGE**

Reviewed target: `methodology/CONTINUOUS_PREDICTION_MARKET_RED_TEAM.md`

Doel van deze review: het plan drie keer vanuit verschillende failure modes proberen te vernietigen en daarna vijf afzonderlijke verbeteringsrondes uitvoeren, met nadruk op hoe prediction-market bots, microstructure researchers, autonomous-science systemen en continuous-red-team programma's dit aanpakken.

## Kill review 1 — epistemic/statistical failure

### Attack

Een autonoom systeem kan duizenden hypotheses/subgroups/parameterizations genereren. Zonder search accounting vindt het gegarandeerd schijnbare winners. Een gewone holdout alleen is onvoldoende als die holdout herhaaldelijk feedback geeft aan het zoekproces.

### External evidence

- Huang et al., ICML 2025, *Automated Hypothesis Validation with Agentic Sequential Falsifications* gebruikt sequentiële falsificatie en expliciete Type-I-errorcontrole voor LLM-gegenereerde hypotheses.
- Moderne autonomous-science systemen scheiden hypothesis generation, experiment/evaluation en persistent memory in plaats van één agent zijn eigen verhaal te laten bevestigen.

### Verdict

Oorspronkelijk plan zonder expliciete adaptive-search governance: **FAIL**.

### Repair

Toegevoegd:

- stable hypothesis/search-family fingerprint;
- aantal geteste subgroups/parameterizations registreren;
- post-hoc subgroup = nieuwe hypothese;
- sequential testing/e-values/alpha/FDR waar passend;
- confirmation/holdout niet als developmentfeedback hergebruiken;
- aparte statistical/data falsifier.

## Kill review 2 — execution/microstructure fantasy

### Attack

Een strategy kan historisch positief lijken maar onuitvoerbaar zijn door shallow depth, korte lifetime, queue uncertainty, latency en partial fills.

### External evidence

- Cheng, Yang & Zou 2026 reconstrueren >75 miljoen Polymarket LOB-snapshots voor 173 NBA-games. Executable single-market anomalies waren zeldzaam; combinatorial opportunities waren vaak ondiep en 76.9% was beperkt tot gemiddeld circa 14.8 shares.
- Young 2026 publiceert een 727M-row synchronized Polymarket/Binance corpus: een 43-feature walk-forward model versloeg de Polymarket orderbook probability niet out-of-sample en gesimuleerde trading was negatief na fricties.
- Publieke trading frameworks gebruiken daarom dry-run/paper defaults, risk managers, event-driven orderbooks en replay; geavanceerdere frameworks voegen queue/fill- en measured-latency modelling toe.

### Verdict

Een plan dat 'candidate -> backtest -> build' gebruikt zonder pre-build execution test: **FAIL**.

### Repair

Toegevoegd:

- economic upper-bound vóór zware replay;
- execution spotcheck vóór build warrant;
- trade-versus-cancel waar mogelijk;
- queue/fill assumptions expliciet;
- latency als gemeten distributie;
- capital lock/opportunity cost;
- conservative execution mode als promotiebasis.

## Kill review 3 — data/provenance failure

### Attack

Zelfs perfecte statistiek faalt als de feedsemantiek fout is. Cross-venue clocks, inferred trade direction, backfills en revisions kunnen causale volgorde en maker/taker conclusies vervalsen.

### External evidence

- Dubach 2026, *The Anatomy of a Decentralized Prediction Market*, koppelt een tick-level Polymarket archive aan on-chain trades en rapporteert dat trade direction uit de publieke feed slechts ongeveer 59–62% met on-chain ground truth overeenkomt; microstructure metrics kunnen hierdoor zelfs van teken veranderen.
- Young 2026 rapporteert expliciet source-clock drift/offset uncertainty ondanks een synchronized corpus.

### Verdict

Een plan zonder source-authority/clock/revision ledger: **FAIL**.

### Repair

Toegevoegd:

- Data Trust Ledger;
- source timestamp + collector receipt timestamp;
- clock uncertainty;
- authoritative direction source;
- revision/backfill policy;
- sequence integrity;
- reconstruction quality;
- fail-closed wanneer semantiek niet bewezen is.

---

# Vijf verbeteringsrondes

## Improvement 1 — van venue folders naar mechanism graph

### Probleem

Een Kalshi-first of venue-first knowledge base herhaalt dezelfde concepten en maakt transfer naar nieuwe venues traag.

### Inspiratie

Continuous exposure-management werkt met stable exposure types en attack-surface inventories; combinatorial-arbitrage research reduceert een enorme relation search via structurele relaties.

### Wijziging

Mechanism Knowledge Graph + Venue Capability Graph.

Nieuwe venue:

`capabilities -> match known mechanism prerequisites -> cheap tests`

Hierdoor hoeft de machine een mechanism class maar één keer conceptueel te leren.

## Improvement 2 — expected-information-gain vóór engineering

### Probleem

Het grootste historische verlies voor dit project is menselijke/engineeringtijd op kandidaten die goedkoop dood hadden gekund.

### Inspiratie

CTEM prioriteert exposures op reële exploitability/impact; autonomous-science systemen gebruiken experiment selection in plaats van alles uit te voeren.

### Wijziging

Pre-Build Killer + build warrant:

`priority ~ expected_information_gain × economic_headroom × transferability × lifetime / engineering_cost × execution_complexity × data_uncertainty`

Geen nieuwe strategy-build als de hypothese niet eerst cheap kill-gates overleeft.

## Improvement 3 — independent adversaries in plaats van self-review

### Probleem

Een hypothesis-generator heeft incentive/bias om coherente verklaringen te behouden.

### Inspiratie

POPPER, Robin, Co-Scientist en Socratic autonomous-science frameworks splitsen generatie, critique/falsification, experiment en evaluatie.

### Wijziging

Minimaal drie onafhankelijke killrollen:

1. Semantic adversary;
2. Statistical/data adversary;
3. Execution/economic adversary.

Plus Independent Reproducer voor high-value candidates.

## Improvement 4 — microstructure-grade execution evidence

### Probleem

Veel publieke bots hebben strategy engines en risk managers, maar simpele simulators behandelen touched price als fill of gebruiken midpoints/hardcoded latency.

### Inspiratie

- Event-driven/hexagonal architectures in publieke Kalshi/Polymarket bots.
- L2 persistence, fill/queue modelling en measured-latency patterns in meer geavanceerde open-source tooling.
- Academic evidence dat prediction-market opportunities vaak shallow en kortlevend zijn.

### Wijziging

Execution Lab met event-driven book reconstruction, sequence-gap invalidation, trade-vs-cancel, queue/fill assumptions, partial-fill states, measured latency distributions en conservative replay.

## Improvement 5 — dark-market intelligence quarantainen maar wel benutten

### Probleem

Dark/illicit markets kunnen unieke governance/reputation/escrow/fraud/resilience mechanismen tonen, maar operationele deelname voegt juridische, custody-, integrity- en evidence-risico's toe en vervuilt de execution-lane.

### External research

Publieke dark-web research gebruikt academische datasets, periodieke scraping/forensische harvesting en netwerk-/marketplace-analyse. Recente DarkCatalog-literatuur benadrukt volatility, deduplication, reproducible evidence bundles en continuous monitoring. Andere studies laten zien dat netwerk- en reputatiesignalen economische uitkomsten kunnen voorspellen binnen cryptomarkets.

### Wijziging

Aparte `knowledge/dark_market_intelligence/` lane:

- intelligence only;
- `source_class: DARK_MARKET_INTELLIGENCE`;
- geen funding/trading/facilitation;
- alleen overdraagbare hypothesen naar reguliere prediction markets;
- provenance/trust expliciet.

---

# Wat anderen doen — samengevat

## Publieke prediction-market bots

Terugkerende patronen:

- adapters per venue;
- event-driven architecture;
- normalized market/orderbook domain objects;
- cross-venue matching;
- paper/dry-run default;
- risk manager en kill switch;
- backtester;
- dashboard/telemetry.

Sterkte: engineeringdiscipline.

Zwakte voor ons doel: vaak begint het systeem met een vooraf gekozen strategy en probeert die daarna te executen; weinig systemen hebben een persistent falsification-first discovery/knowledge layer.

## Academic microstructure research

Terugkerende patronen:

- volledige tick/L2 archives;
- authoritative trade records;
- pre-registered panels;
- walk-forward/OOS;
- fill/depth/lifetime realism;
- negative results publiceren.

Sterkte: veel beter geschikt als bewijsstandaard.

## Autonomous-science agents

Terugkerende patronen:

- gespecialiseerde rollen;
- generate -> critique -> experiment -> evaluate;
- persistent memory;
- iterative refinement;
- formal/causal falsification.

Sterkte: dit lijkt het meest op onze gewenste researchfactory.

## Continuous red-team / CTEM

Terugkerende cyclus:

`scope -> discovery -> prioritization -> validation -> mobilization`

Sterkte: voorkomt 'scan everything equally' en maakt knowledge reuse centraal.

---

# Eindverdict na 3× kill + 5× improvement

Het oorspronkelijke idee — een doorlopend AI-systeem dat prediction markets 'pentest' — is **conceptueel sterk genoeg om V0 te bouwen**, maar alleen in de aangepaste vorm:

1. venue-agnostic mechanism graph;
2. Pre-Build Killer vóór engineering;
3. multiple-hypothesis governance;
4. onafhankelijke falsifiers;
5. Data Trust Ledger;
6. microstructure-grade Execution Lab;
7. dark-market lane strikt intelligence-only;
8. deterministic execution, AI buiten de hot path.

De belangrijkste overgebleven onzekerheid is economisch, niet technisch: het systeem kan uitstekend functioneren en alsnog `NO_PROVEN_EDGE` vinden.

## Bronnen

- https://proceedings.mlr.press/v267/huang25n.html
- https://www.nature.com/articles/s41586-026-10652-y
- https://doi.org/10.1038/s41586-026-10644-y
- https://ctem.org/docs/stages
- https://arxiv.org/abs/2605.00864
- https://arxiv.org/abs/2607.26245
- https://arxiv.org/abs/2604.24366
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6615739
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7115858
- https://arxiv.org/abs/2609.12878
- https://github.com/cryptuon/polybot
- https://github.com/Viprasol-Tech/kalshi-trading-bot
- https://github.com/zostaff/poly-arbitrage-bot
- https://github.com/braedonsaunders/homerun
- https://doi.org/10.1145/3615666
- https://www.sciencedirect.com/science/article/pii/S2666281726000673
- https://www.nature.com/articles/s41598-024-67115-5
