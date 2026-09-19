# Source inventory — 2026-09-19

Dit document registreert bestaande GitHub-research die bij de bootstrap van de centrale knowledge base is aangetroffen. Het kopieert bewust geen credentials/accountdetails uit private repositories.

## bas1231/predictionbot

### Researchfolder
`onderzoek/`

Aangetroffen:
- `KALSHI_COMPLEX_STRATEGY_HUNT_2026-09-19.md`
- `PREDICTION_MARKET_NEW_MATH_RESEARCH_2026-09-19.md`
- `FORECASTEX_COUPON_AND_YIELD_RESEARCH_2026-09-19.md`
- `ORACLE_BOND_MARKET_HEDGE_RESEARCH_2026-09-19.md`
- `STATE_DEPENDENT_CONVERSION_GRAPH_RESEARCH_2026-09-19.md`

Belangrijkste researchfamilies: Kalshi cross-book/contract algebra, MVE/combos, deadline/nesting, scalar/DNP, correlation/joint probability, carry/coupon overlays, protocol-state conversion graphs, oracle-bond/outcome-token combinaties.

Economische status van de aangetroffen research: **NO_PROVEN_EDGE**.

## bas1231/proof-hunter

Meest gevorderde aangetroffen branch bij inventarisatie:
`ai/phase15-mecnet-discovery-watch-v0`

Belangrijke experimentreeks:
- PH-E001 contract/rules inventory;
- PH-E002 TWC finality observability;
- PH-E003 prospective Source Lock overlap;
- PH-E004/B BTC15m source-lock research;
- PH-E005 predicate normalizer;
- PH-E006 theorem engine;
- PH-E007 relation discovery;
- PH-E008 structured-strike compiler;
- PH-E009 settlement-domain gate;
- PH-E010 mutual-exclusion floor;
- PH-E011 binary payout provenance;
- PH-E012 unconditional pre-settlement floor gate;
- PH-E013 collateral metadata;
- PH-E014 MECNET semantics;
- PH-E015 account netting/event-lock gate;
- PH-E016 executable six-leg pricing gate;
- PH-E016B/C prospective depth/generalized MECNET discovery follow-ups.

Belangrijkste duurzame conclusies:
- TWC `no_report` / `preliminary` / `official` states waren observeerbaar en fail-closed classificeerbaar.
- KXHIGHNY structured strikes konden machineleesbaar naar predicates worden gecompileerd.
- Zes KXHIGHNY buckets/tails waren pairwise disjoint in de onderzochte event-instance.
- Een conditionele standaard-path six-NO floor van $5 kon worden afgeleid, maar **niet** tot unconditional settlement guarantee worden gepromoveerd wegens exception states.
- Kalshi eventmetadata liet `mutually_exclusive=true` en `collateral_return_type="MECNET"` zien voor de onderzochte event-instance.
- De $5 MECNET-structuur is een collateral/offset benchmark, niet gedocumenteerd als extra gratis/withdrawable cash.
- Authenticated read-only account/event-lock evidence haalde een tussengate, maar dit bewees geen economische edge.
- Executable six-leg pricing/atomicity/post-fill collateral accounting/repeatability bleven aparte gates.

Economische status: **NO_PROVEN_EDGE**.

## bas1231/market_algebra

Aangetroffen documentatie:
- `docs/BUILD_PLAN.md`
- `docs/EXPERIMENT_001.md`
- `docs/NEGATIVE_EVIDENCE.md`
- `docs/RESEARCH_LOG.md`

Pre-registered Experiment 001 onderzoekt prospective executable inconsistencies in:
1. soccer 3-way partition (control);
2. soccer cross-product identities;
3. hourly-weather adjacent thresholds;
4. U-3 unemployment als semantic/reference lane.

Belangrijke negatieve evidence: handmatige spot-check van minstens 12 actuele regulation-time soccer 3-way sets gaf zichtbare YES-baskets van circa 101–105 cent voor 100 cent payout vóór fees. Geen simpele 3-way arb aangetoond.

## bas1231/live_watcher

Belangrijke documenten:
- `docs/KILL_CHECK_2026-09-18.md`
- `docs/LW0015_VALIDATION_2026-09-19.md`
- `docs/LW0016_SHADOW_CENSUS.md`
- `docs/LW0017_SETTLEMENT_BOTTLENECK.md`

Duurzame conclusies:
- Execution-context observability is technisch gevalideerd maar post-L2 context bewijst niet exact de state op het L2-moment.
- Oude captures mogen ontbrekende lifecycle/finality context niet achteraf uit latere data reconstrueren.
- Eerste census: 42 confirmations / 20 unieke milestones; 3 met positieve `net_lower_bound_dollars`; alle 3 eindigden op `SETTLEMENT_UNPROVEN`.
- Ontbrekende historische finality-details zijn expliciet `LEGACY_DETAIL_UNAVAILABLE`.
- Soccer state-lock V1 heeft vooraf een killregel: na 100 onafhankelijke proven-lock episodes zonder één volledig geldige positieve episode wordt de hypothese `HYPOTHESIS_KILLED`.

Economische status: **NO_PROVEN_EDGE**.

## bas1231/strix-research-control

Deze repo bevat historische Runner-research en grote resultaatbestanden. Relevante aangetroffen resultaten:
- `master-economic-evidence-counts-v1.json`: 47,377 masterregels; 6,855 BUY decisions; 3,120 EXECUTED; 3,117 trades met final-profit/paper-PnL velden.
- `focused-runner-research-20260912-v1.json`: 46,963 launches / 23,528,509 compact records in de gebruikte cache; geen entry candidates gepromoveerd; nieuwste historische holdout bleef ongeopend; geen economic PnL claim.
- `early-sell-absorption-20260913-v1.json`: 3,117 eligible historical trades; sommige absorption/sell-pressure scores verrijkten extreme-winner targets, maar de zichtbare geselecteerde groepen hadden negatieve gemiddelde/mediane en leave-top-k PnL-statistieken. Resultaat is development evidence, geen pristine confirmation.

Dit materiaal is vooral nuttig als anti-overfitting/negative-evidence precedent. Het is geen Kalshi-edgebewijs.

## bas1231/runner_v21

Grote oudere Runner-codebase met intelligence/optimizer/resultbestanden. De centrale README is leeg en de repo is geen schone prediction-market research ledger. Voor deze knowledge base wordt de repo daarom alleen als historische bron geregistreerd; de gecontroleerde samenvattingen uit `strix-research-control` hebben voor researchconclusies voorrang.

## Niet inhoudelijk geïmporteerd

Niet-prediction repos of lege/onrelevante repositories zijn niet in de knowledge graph opgenomen.

## Ingestbeleid

Nieuwe sessies mogen rechtstreeks naar deze centrale repo schrijven. Bij conflicten geldt:
- nooit negatieve evidence verwijderen;
- nieuwere evidence krijgt een nieuwe record/versie;
- oorspronkelijke repo/ref/path blijft provenance;
- een status mag alleen worden gepromoveerd als de bijbehorende gate expliciet is gehaald.
