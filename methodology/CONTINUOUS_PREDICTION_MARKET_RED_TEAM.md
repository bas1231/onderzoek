# Continuous Prediction Market Red Team

Datum: 2026-09-19
Status: **METHODOLOGY — RESEARCH ONLY — NO_PROVEN_EDGE**

## 1. Missie

Bouw een steeds groeiend, venue-onafhankelijk onderzoeksstelsel dat prediction markets continu behandelt als een economisch en contractueel attack surface.

Doel:

> ontdek, formaliseer, falsificeer en execution-realistisch valideer legale economische zwaktes in prediction markets; bouw cumulatieve machine-leesbare kennis op zodat nieuwe venues, producten en states automatisch tegen bekende én nieuwe mechanismen kunnen worden getest.

Het systeem is geen strategie-generator die moet bewijzen dat winst bestaat. Het is een falsificatiegedreven edge-fabriek die zoveel mogelijk slechte ideeën goedkoop elimineert en alleen survivors promoveert.

Economische default: `NO_PROVEN_EDGE`.

## 2. Scope

De researchscope is wereldwijd en venue-onafhankelijk. Onder meer in scope:

- gereguleerde event-contract exchanges;
- crypto-native prediction markets;
- CLOB-, AMM-, RFQ-, combo- en conditional-producten;
- bookmaker/prediction-hybrids waar contract- en executiondata vergelijkbaar zijn;
- nieuwe, kleine en tijdelijke venues;
- publieke documentatie, API's, rulebooks, settlement/oracle-mechanismen en publieke orderflow;
- dark-web/illicit-market intelligence als afzonderlijke intelligencebron, uitsluitend om mechanismen, failures, incentives en overdraagbare hypotheses te leren kennen.

### Dark-web / illicit-market intelligence

Dark-web of illegale markten zijn **geen execution-lane**. Geen storten, handelen, kopen, verkopen, faciliteren, credential-/identiteitsmisbruik of deelname aan illegale marktactiviteit.

Wel toegestaan als intelligence:

- publieke academische datasets en papers;
- publieke threat-intelligence- en OSINT-rapporten;
- historische/forensische datasets;
- publiek indexeerbare beschrijvingen van marktmechanismen;
- analyse van governance, escrow, reputation, settlement, incentive design, fraud/scam patterns, market lifecycle en resilience;
- hypotheses vertalen naar legaal testbare analogieën op reguliere prediction markets.

Alle dark-market findings krijgen `source_class: DARK_MARKET_INTELLIGENCE` en mogen nooit zelfstandig execution autoriseren.

## 3. Harde grens

`ILLEGAL = HARD STOP`.

Agressief, ongebruikelijk, onbedoeld en legaal grijs economisch onderzoek is welkom. Dat iets een venue geld kost, onverwacht is of niet door ontwerpers voorzien lijkt, is geen reden om het af te wijzen.

Niet in scope voor operationele research of uitvoering:

- fraude;
- diefstal;
- marktmanipulatie;
- spoofing;
- wash trading;
- collusie;
- misleiding;
- credentialmisbruik;
- ongeautoriseerde toegang;
- sabotage;
- gestolen/niet-publieke vertrouwelijke informatie;
- operationeel misbruik van software/securitykwetsbaarheden;
- toegangscontroles omzeilen om toegang te verkrijgen die niet is toegestaan.

Publiek bekende securityproblemen mogen defensief als mechanism/risk/negative-evidence worden opgeslagen zonder exploit-instructies.

## 4. Werkmodel: economic CTEM

Gebruik een continue cyclus die analoog is aan Continuous Threat Exposure Management:

`SCOPE -> DISCOVER -> PRIORITIZE -> VALIDATE -> MOBILIZE/LEARN -> opnieuw`

Voor prediction markets betekent dit:

1. **Scope** — inventariseer venue, producten, regels, sources, oracle, collateral, fees, ordermodel en lifecycle.
2. **Discover** — projecteer bekende mechanismen op de venue en zoek nieuwe interacties/anomalieën.
3. **Prioritize** — rangschik op economic headroom, novelty, lifetime, execution feasibility, benodigde engineering en informatieopbrengst.
4. **Validate** — falsificeer semantiek, data, statistiek en execution vanuit onafhankelijke failure modes.
5. **Mobilize/Learn** — alleen survivors krijgen extra tooling/shadow; negatives en proof-obligations gaan terug naar de knowledge graph.

Discovery volume is geen succesmetric. De primaire efficiency-metric is hoeveel verkeerde ideeën vroeg en goedkoop worden vernietigd.

## 5. Venue Capability Graph

Iedere venue krijgt een versioned machine-readable capability profile, bijvoorbeeld:

```yaml
venue_id: polymarket
as_of: 2026-09-19
market_model: CLOB
collateral: USDC
resolution:
  mechanism: oracle
  details: versioned
products:
  binary: true
  multivariate: ...
  scalar: ...
public_orderbook: true
public_trades: true
trade_direction_authority: ...
fees: ...
rewards: ...
settlement_exceptions: []
lifecycle_states: []
data_trust_tier: ...
```

Mechanismen krijgen eigen prerequisites:

```yaml
mechanism_id: MECH-PARTITION-001
requires:
  - multiple representations of same world-state
  - provable payoff relation
  - contemporaneous executable prices
```

De engine berekent automatisch `venue × mechanism` matches. Nieuwe venues worden hierdoor direct tegen bestaande mechanismen getest.

## 6. Mechanism Knowledge Graph

Kennis wordt niet primair per venue opgeslagen maar per mechanisme, met relaties naar venues, experiments en negative evidence.

Voorbeelden:

- payout identity / dominance;
- threshold / range / exact / bucket partitioning;
- scalar/DNP/void/fair-price settlement;
- first/stable decidability;
- oracle/source lag;
- collateral/netting/carry;
- maker/taker/adverse selection;
- favorite-longshot / probability weighting;
- framing / affirmative wording / unpacking;
- FOMO/herding/salience;
- revision lag;
- cross-venue semantic asymmetry;
- fee/reward discontinuities;
- lifecycle/early-close/cancel states;
- state-dependent conversion;
- combinatorial/subset/superset relations.

Iedere relation moet provenance en versie hebben. Conflicterend bewijs wordt naast elkaar opgeslagen.

## 7. Candidate lifecycle

```text
OBSERVATION
  -> HYPOTHESIS_UNTESTED
  -> PREBUILD_CANDIDATE
  -> STRUCTURAL_CANDIDATE
  -> REPLAY_POSITIVE
  -> VALIDATION_POSITIVE
  -> HOLDOUT_POSITIVE
  -> SHADOW_POSITIVE
  -> MICRO_LIVE_CANDIDATE
  -> PROVEN_EDGE
```

Een failure kan leiden tot:

- `TESTED_NEGATIVE`;
- `EXECUTION_BLOCKED`;
- `SEMANTICALLY_INVALID`;
- `INSUFFICIENT_DATA`;
- `DUPLICATE_KNOWN_WEAK`;
- `NO_PROVEN_EDGE`.

Geen statuspromotie zonder expliciete gate-evidence.

## 8. Pre-Build Killer

Nieuwe engineering is duur. Nieuwe strategycode mag daarom niet de standaardreactie op een idee zijn.

### Gate 0 — novelty / prior art

- Zoek knowledge graph en negative ledger.
- Bepaal of het idee werkelijk nieuw is of slechts herformulering.

### Gate 1 — semantic/rules viability

- Exacte payoutfunctie en lifecycle.
- Source, measurement window, rounding, revision, void/DNP/cancel/scalar/fair-price/finality.
- Voor cross-venue: payoff-equivalence voor iedere toegestane state.

### Gate 2 — economic headroom

Bereken vóór zware replay een conservatieve bovengrens:

`max_plausible_surplus - minimum_unavoidable_friction`

Als zelfs een gunstige upper bound niet genoeg ruimte laat voor spread/fees/slippage/legging/capital-time risk: kill.

### Gate 3 — cheap empirical falsification

Gebruik bestaande data en vooraf vastgelegde tests. Rapporteer minimaal:

- onafhankelijke event-count;
- median/mean/winsorized effect;
- cluster-aware uncertainty;
- top-k/outlier concentration;
- regime/category stability;
- alternative rational explanation.

### Gate 4 — execution spotcheck

Gebruik echte point-in-time books/trades waar beschikbaar. Geen midpoint/last/UI chance.

### Gate 5 — build warrant

Nieuwe code alleen als:

```text
novelty              PASS
semantics            PASS
economic_headroom    PASS
cheap_empirical      PASS
execution_spotcheck  PASS
expected_information_gain > build_cost_threshold
```

Output: `BUILD_APPROVED`, anders geen strategy-build.

## 9. Multiple-hypothesis / adaptive-search control

Een autonome edge-fabriek die duizenden hypotheses test, creëert automatisch false positives. Daarom:

- iedere hypothese krijgt vóór evaluatie een stable fingerprint;
- dezelfde data mogen niet onbeperkt opnieuw als 'nieuw bewijs' worden gebruikt;
- development en confirmation worden strikt gescheiden;
- post-hoc subgroups worden nieuwe hypotheses;
- gebruik waar passend sequential-testing/e-value/alpha-spending of vooraf gedefinieerde family-wise/FDR-regels;
- rapporteer hoeveel hypotheses, subgroups en parameterizations zijn geprobeerd;
- een kandidaat mag niet promoveren op nominale p-waarde zonder search-budget/context;
- holdout en prospective shadow blijven verplicht voor economische promotie.

## 10. Drie onafhankelijke kill reviews

Iedere serieuze survivor krijgt drie verschillende red-teamrollen:

### A. Semantic adversary

Doel: bewijs dat de wereldstate/payoffrelatie verkeerd is geïnterpreteerd.

### B. Statistical/data adversary

Doel: bewijs dat het resultaat veroorzaakt wordt door lookahead, selection bias, multiple testing, dependence, stale data, clock mismatch of outliers.

### C. Execution/economic adversary

Doel: bewijs dat echte fills, queue, fees, latency, slippage, partial fills, inventory/collateral/capital lock of finality de edge vernietigen.

Waar mogelijk gebruikt ten minste één reviewer een onafhankelijke implementatie of dataset.

## 11. Data Trust Ledger

Iedere datasource krijgt expliciete trust properties:

- source authority;
- observation timestamp;
- collector receipt timestamp;
- clock uncertainty;
- revision policy;
- completeness;
- sequence integrity;
- direction authority;
- survivorship risk;
- historical reconstruction quality.

Belangrijk: venue-feeds mogen geen semantiek erven die ze niet aantoonbaar bevatten. Bijvoorbeeld trade direction of maker/taker-labels moeten uit een autoritatieve bron komen als feed inference onvoldoende betrouwbaar is.

## 12. Execution Lab

Backtests moeten de feitelijke marktmechanica modelleren.

Minimaal:

- event-driven orderbook reconstruction;
- sequence-gap invalidation;
- trade-versus-cancel decomposition waar data dit toelaat;
- queue/fill assumptions expliciet;
- latency als gemeten distributie, niet één optimistische constante;
- maker en taker apart;
- partial-fill/legging states;
- capital lock en opportunity cost bij cross-venue;
- settlement/finality/correction risk;
- conservative execution mode als promotiebasis.

Een prijsniveau dat is aangeraakt bewijst geen fill.

## 13. Behavioral Red Team

Menselijke voorspelbaarheid wordt gemodelleerd als marktmechanisme, niet als verhaal over individuele personen.

Onderzoek onder meer:

- favorite-longshot/lottery demand;
- affirmative framing / optimism tax;
- FOMO/herding;
- partition dependence/unpacking;
- surprise over/underreaction;
- salience/fandom/attention;
- recency/anchoring;
- round-number effects.

Bouw altijd een informed-flow veto. One-sided flow kan behavioral surplus zijn maar kan ook geïnformeerde flow zijn.

Candidate architecture:

`behavioral pressure -> informed-flow risk -> fair-value anchor -> executable quote -> markout/fill/settlement`

Geen targeting/deanonymisering van kwetsbare individuele traders; analyseer geaggregeerde publieke flow/cohorten.

## 14. Research roles

Geen agent mag zijn eigen hypothese genereren, valideren en promoveren zonder onafhankelijke controle.

Rollen:

- **Scout** — nieuwe venues/data/mechanismen;
- **Hunter** — formuleert concrete hypotheses;
- **Prioritizer** — expected-information-gain/build-cost/economic-headroom;
- **Semantic Falsifier**;
- **Data/Statistics Falsifier**;
- **Execution Falsifier**;
- **Independent Reproducer**;
- **Judge** — statuspromotie volgens vaste gates;
- **Memory Curator** — dedup, supersedes, conflicts, negative evidence.

De meeste rollen kunnen deterministische code zijn. LLM/ChatGPT is vooral geschikt voor discovery, rule interpretation, literature search, adversarial explanation search en experiment design; execution blijft deterministic.

## 15. Prioriteringsfunctie

Gebruik geen 'interessantheid' alleen. Rank bijvoorbeeld op:

`priority = expected_information_gain × plausible_economic_headroom × transferability × opportunity_lifetime / (engineering_cost × execution_complexity × data_uncertainty)`

Dit is een research-ranking, geen winstclaim.

Extra bonus voor hypotheses die:

- meerdere venues tegelijk kunnen falsificeren;
- een hele mechanism class kunnen sluiten;
- weinig nieuwe code vereisen;
- bestaande immutable data gebruiken;
- voldoende opportunity lifetime hebben voor retail-infrastructuur.

## 16. Wat anderen doen — en wat wij overnemen

### Open-source prediction bots

Veel publieke bots gebruiken:

- event-driven venue adapters;
- typed orderbooks/markets;
- dry-run/paper-by-default;
- afzonderlijke risk manager;
- backtest/replay;
- kill switches;
- cross-venue matching;
- dashboards/telemetry.

Deze patronen nemen we over voor infrastructuur, maar niet de vaak impliciete aanname dat een strategy-idee al voldoende is om te bouwen.

### Geavanceerdere microstructure tooling

Publieke research/frameworks laten het belang zien van:

- volledige L2 persistence;
- trade-vs-cancel onderscheid;
- queue/fill modelling;
- gemeten latency;
- authoritative trade direction;
- walk-forward out-of-sample tests.

Deze worden proof obligations voor execution-sensitive lanes.

### Autonomous-science systemen

Moderne autonomous-discovery frameworks scheiden hypothesis generation, critique/falsification, experiment, evaluation en persistent memory. Dit bevestigt onze keuze voor onafhankelijke agents en falsification-first orchestration.

### Continuous red-team / CTEM

Continuous exposure management werkt via scope -> discovery -> prioritization -> validation -> mobilization. We hergebruiken dit als economische attack-surface lifecycle, met stable mechanism IDs en een evidence-backed exposure/candidate register.

## 17. Vijf verplichte verbeteringsloops

Iedere architectuur- of methodology-release ondergaat vijf reviews:

1. **Waste review** — wat kunnen we eerder/goedkoper killen voordat nieuwe code nodig is?
2. **False-positive review** — welke adaptive-search, leakage, dependency of multiple-testing route kan ons misleiden?
3. **Execution review** — welke fill/queue/latency/depth/settlement/capital assumption is te gunstig?
4. **Transfer review** — welke kennis moet venue-agnostisch als mechanisme worden opgeslagen zodat andere venues automatisch profiteren?
5. **Adversarial-source review** — welke bron, clock, revision, on-chain/off-chain of dark-market provenance kan fout/onbetrouwbaar/stale zijn?

Een plan dat na deze vijf rondes niet verandert is verdacht: documenteer expliciet waarom geen wijziging nodig was.

## 18. Minimal viable factory

Bouwvolgorde:

### V0 — Knowledge + Pre-Build Killer

- mechanism graph;
- venue capability profiles;
- candidate schema;
- negative-evidence lookup;
- semantic gate;
- economic upper-bound gate;
- cheap empirical runner;
- execution spotcheck interface;
- build warrant.

### V1 — Shared immutable data + execution lab

- venue adapters;
- raw event store;
- normalized Parquet/DuckDB;
- clocks/provenance;
- L2 replay;
- fee/fill/latency models.

### V2 — Autonomous discovery

- Scouts/Hunters;
- mechanism matching;
- hypothesis queue;
- independent falsifiers;
- prioritizer;
- Judge;
- Git knowledge export.

### V3 — Prospective shadow

Alleen validated survivors.

### V4 — Micro-live

Alleen afzonderlijk geautoriseerde strategies die holdout + shadow + execution proof hebben gehaald.

## 19. Success metrics

Niet alleen P&L meten.

Research-system metrics:

- hypotheses generated;
- duplicate rate;
- median cost/time-to-kill;
- percentage killed vóór nieuwe code;
- false-positive retention;
- proportion with independent reproduction;
- knowledge reuse across venues;
- execution-block rate;
- shadow survival rate;
- engineering hours per promoted candidate;
- unresolved evidence debt.

Economische metrics blijven na kosten en risico's de uiteindelijke beslisser.

## 20. Externe inspiratie / provenance

- Huang et al., "Automated Hypothesis Validation with Agentic Sequential Falsifications" (ICML 2025 / PMLR 267).
- Nature 2026, "A multi-agent system for automating scientific discovery" (Robin).
- Nature 2026, "Accelerating scientific discovery with Co-Scientist".
- CTEM.org, Five Stages of CTEM: Scoping, Discovery, Prioritization, Validation, Mobilization.
- Cheng et al. 2026, "Arbitrage Analysis in Polymarket NBA Markets".
- Young 2026, "OpenMarket: A Synchronized Polymarket-Binance Dataset for High-Frequency Prediction-Market Research".
- Dubach 2026, "The Anatomy of a Decentralized Prediction Market: Microstructure Evidence from the Polymarket Order Book".
- Bartlett & O'Hara 2026, "Adverse Selection in Prediction Markets: Evidence from Kalshi".
- Cardozo & Rivero-Wildemauwe 2026, "The Favorite-Longshot Bias in Prediction Markets: Evidence from Polymarket".
- Curtin 2026, "Zero Edge, Cheaply".
- Public open-source frameworks reviewed 2026-09-19: PolyBot, Viprasol Kalshi Trading Bot, several Kalshi/Polymarket arbitrage bots, and HomeRun; architecture claims are treated as community/open-source evidence, not proof of profitability.
- Dark-market intelligence methodology references include public academic dark-web marketplace datasets/forensics literature; no illicit-market participation is required or authorized by this plan.
