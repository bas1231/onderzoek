# Prediction Market Research Knowledge Base

Status: **RESEARCH ONLY — NO_PROVEN_EDGE**

Deze repository is de canonieke, agent-leesbare kennislaag voor onderzoek naar prediction markets. De eerste venue is **Kalshi**. Het doel is niet om winstgevendheid te veronderstellen, maar om bekende feiten, hypotheses, falsificaties, experimenten en execution-beperkingen zodanig vast te leggen dat AI-agents nieuwe toetsbare verbanden kunnen ontdekken zonder eerder onderzoek steeds opnieuw te doen.

## Harde onderzoeksregel

Een interessante formule, prijsafwijking of mechanisme is geen edge. Promotie vereist minimaal:

`rules/payoff proof -> point-in-time executable data -> fees/depth/slippage -> historische execution-realistische replay -> validation -> untouched holdout -> prospectieve shadow/canary -> pas daarna eventueel micro-live`

`NO_PROVEN_EDGE` is een geldig eindresultaat.

## Repository-rol

Deze repo is de **kennisindex en canonieke researchlaag**. Grote ruwe datasets/orderbook-tapes horen buiten Git; hier bewaren we hun manifests, hashes, conclusies en provenance.

Belangrijk: deze repository stond bij bootstrap publiek. Daarom worden hier geen credentials, API keys, private accountdetails, geheime evidence-paden of andere gevoelige gegevens gekopieerd. Bronrepo's kunnen privé zijn; verwijzingen naar repo/pad/branch dienen als provenance.

## Structuur

- `meta/` — broninventaris, ingeststatus en repository-provenance.
- `methodology/` — vaste onderzoeks- en bewijsregels voor mensen en agents.
- `knowledge/kalshi/` — machine-leesbare Kalshi claims, hypotheses en resultaten.
- `knowledge/cross_venue/` — relevante mechanismen van andere prediction venues/protocollen.
- `negative_evidence/` — gefalsificeerde of verzwakte ideeën; nooit verwijderen omdat ze niet werkten.

## Statusvocabulaire

- `FACT_VERIFIED` — rechtstreeks ondersteund door primaire/documentaire of gereproduceerde evidence.
- `OBSERVED` — point-in-time waargenomen, maar geen algemene claim.
- `HYPOTHESIS_UNTESTED` — toetsbare hypothese zonder voldoende test.
- `TESTED_NEGATIVE` — hypothese/route is door de vastgelegde test niet ondersteund of formeel afgesloten.
- `STRUCTURAL_CANDIDATE` — geldig mechanisme, maar economische/execution-edge nog onbewezen.
- `RESEARCH_POSITIVE` — een tussengate is gehaald; dit betekent nadrukkelijk niet winstgevend.
- `NO_PROVEN_EDGE` — huidige economische standaardstatus.

## Agentregel

Agents mogen hypotheses combineren en nieuwe candidates voorstellen, maar moeten altijd:

1. bestaande negatieve evidence controleren;
2. bron + datum + point-in-time beschikbaarheid bewaren;
3. onderscheid maken tussen payout-identiteit, signal edge en market edge;
4. tegenstrijdige evidence bewaren in plaats van overschrijven;
5. nooit later beschikbare informatie terugprojecteren;
6. nooit `PROVEN_EDGE` afleiden uit alleen backtest, UI-prijs, midpoint, last trade of theoretische payoff;
7. nieuwe post-hoc ideeën opnieuw op untouched data testen.

## Scopegrens

Onderzoek naar legale contract-, settlement-, collateral-, fee-, information-, behavioral- en microstructurele inefficiënties is in scope. Marktmanipulatie, fraude, KYC-omzeiling, misleiding, sabotage en operationeel misbruik van softwarekwetsbaarheden zijn niet in scope. Publieke security-/incidentinformatie mag wel als defensieve of falsificatiecontext worden vastgelegd zonder exploit-instructies.
