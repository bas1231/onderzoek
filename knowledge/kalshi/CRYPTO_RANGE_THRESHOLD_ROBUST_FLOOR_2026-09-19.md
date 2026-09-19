# Crypto range ↔ threshold robust locked floor

Datum: 2026-09-19
Status: **STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Kernvondst

Kalshi biedt voor dezelfde crypto, datum en settlementtijd zowel threshold-contracten als range-contracten. Wanneer een lower threshold `A`, upper threshold `H` en tussenliggende range `R` op **dezelfde settlement key** zijn gebaseerd, ontstaat een robuuste drie-leg payout-floor die géén exacte threshold-difference identity vereist.

Definieer:

- `A`: lower threshold, bijvoorbeeld DOGE `0.085 or above` / formeel een comparator net onder 0.085;
- `H`: upper threshold, bijvoorbeeld DOGE `0.09 or above`;
- `R`: tussenliggende range, bijvoorbeeld DOGE `0.0850000 to 0.0899999`.

Wanneer de concrete rules/source/timestamp aantonen dat:

- `H subset A`;
- `R subset A`;
- `H intersect R = empty`;

volgt voor standaard binaire settlement:

`YES(A) + NO(H) + NO(R)`

met payout:

`A + (1-H) + (1-R) = 2 + A - H - R >= 2`.

Dus de portfolio heeft een **minimum payout van $2** onder iedere normale binary settlementstate.

Dit is sterker dan de exacte identity `R = A - H`, omdat kleine boundary-gaps tussen threshold en range de floor niet breken. In zulke gap-states kan de payout juist hoger worden.

## State-table

Voor een canonical lower/range/upper structuur:

| Onderlying state | A | H | R | Portfolio payout |
|---|---:|---:|---:|---:|
| beneden lower threshold | 0 | 0 | 0 | 2 |
| eventuele lower boundary-gap | 1 | 0 | 0 | 3 |
| in range R | 1 | 0 | 1 | 2 |
| eventuele upper boundary-gap | 1 | 0 | 0 | 3 |
| boven upper threshold | 1 | 1 | 0 | 2 |

De precieze gapbreedte hoeft dus niet nul te zijn om de floor te bewijzen.

## Primaire settlementsemantiek

Kalshi's actuele Crypto Markets-documentatie stelt dat crypto price contracts worden afgerekend op een gemiddelde van zestig één-seconde observaties van de relevante CF Benchmarks Real-Time Index rond de settlementtijd.

De actuele CRYPTO contract terms specificeren onder meer:

- underlying = spot price volgens een eenvoudige 60-seconden average van de opgegeven CF Benchmarks index;
- Source Agency = CF Benchmarks;
- `Above X` = strikt groter dan X;
- `At least X` = X of groter;
- `Between X and Y` = groter of gelijk aan X en kleiner of gelijk aan Y;
- bij geen/onvolledige data op expiration time resolve affected strikes to No.

Bronnen:
- https://help.kalshi.com/en/articles/13823838-crypto-markets
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/RIPPLE.pdf

De relation mag alleen worden geactiveerd wanneer asset/index/date/time/source en de concrete comparator/bounds van alle drie legs exact zijn gebonden.

## No-data branch

De CRYPTO terms zeggen dat bij geen of onvolledige data op expiration time de affected strikes naar No resolven.

Als alle drie gerelateerde strikes door dezelfde ontbrekende underlying-data worden geraakt, is de portfolio-payout:

`YES(A)=0, NO(H)=1, NO(R)=1 => $2`.

Dus deze expliciete no-data branch breekt de floor niet.

## Contingency / interpretation blocker

De volledige **unconditional** theorem-gate is nog NIET groen.

Kalshi Rulebook v1.24 Rule 6.3(a) beschrijft normale binary settlement. Rule 6.3(c) geeft Kalshi discretionaire interpretatie/payout authority wanneer niet kan worden vastgesteld of de Expiration Value binnen het Payout Criterion valt of de payout anderszins niet kan worden bepaald.

De bekeken CRYPTO terms bevatten daarnaast een contingency-verwijzing waarvan de nummering niet zonder meer overeenkomt met de huidige Rulebook-structuur. Daardoor mag niet worden aangenomen dat iedere uitzonderlijke contingency automatisch dezelfde binaire relation preserveert.

Status:

- standaard binary settlement: **FORMALLY PROVEN FLOOR**;
- expliciete common no-data branch: **FLOOR PRESERVED**;
- overige contingency/Outcome Review interpretation: **UNCONDITIONAL FLOOR NOT YET PROVEN**.

Bron:
- https://kalshi-public-docs.s3.amazonaws.com/regulatory/rulebook/Kalshi%20Rulebook%20v1.24.pdf

## Concrete DOGE discovery — 2026-09-19 17:00 EDT event

Publieke/current-ish bronnen tonen tegelijkertijd de productfamilies:

- threshold event `KXDOGED-26SEP1917` — Dogecoin price at Sep 19, 2026 at 5pm EDT;
- range event `KXDOGE-26SEP1917` — Dogecoin price range at Sep 19, 2026 at 5pm EDT.

CoinRithm rapporteerde rond dezelfde onderzoeksperiode onder meer:

- threshold chance rond 86% voor `$0.085 or above`;
- threshold chance rond 10% voor `$0.09 or above`;
- range `$0.085 to 0.0899999` selected display `Yes 83c / No 17c` in één crawl.

Coinbase's DOGE prediction overview toonde eveneens beide same-time productfamilies, maar de displayed percentages varieerden tussen crawls/locales. Daarom zijn deze waarden **discovery only**, niet simultaneous execution evidence.

Bronnen:
- https://www.coinrithm.com/en/prediction-markets/kalshi/kxdoged-26sep1917
- https://www.coinrithm.com/en/prediction-markets/kalshi/kxdoge-26sep1917
- https://www.coinbase.com/predictions/crypto/DOGE
- https://kalshi.com/category/crypto/doge

## Illustratieve fee test — NIET execution proof

Een niet-simultane, current-ish displaycombinatie uit meerdere crawls kan illustratief worden geschreven als:

- `YES(A_low)` ≈ 89c;
- `NO(H_high)` ≈ 87c;
- `NO(R)` ≈ 18c;
- totaal ≈ 194c;
- standard-settlement floor = 200c;
- bruto gap = 6c.

Deze combinatie is **niet** als fillable quote vastgesteld en mag niet als arbitrage worden gerapporteerd.

Onder de algemene feeformule, illustratief met `k=0.07` en exact deze drie tradeprijzen:

- quantity 1: rounded fees ≈ 1c + 1c + 2c = 4c; bruto 6c; ≈ 2c over vóór slippage/legging;
- quantity 10: totale rounded fee ≈ $0.26; bruto $0.60; ≈ $0.34 over vóór slippage/legging;
- quantity 100: totale rounded fee ≈ $2.53; bruto $6.00; ≈ $3.47 over vóór slippage/legging.

Deze berekening bewijst alleen dat de **orde van grootte** groot genoeg kan zijn om nader L2-onderzoek te rechtvaardigen. Runtime fee state/overrides en fillfragmentatie moeten point-in-time worden gebonden.

Bron fees:
- https://help.kalshi.com/en/articles/13823805-fees
- https://kalshi.com/regulatory/fee-schedule

## Historische execution-data beschikbaar voor range-leg

CryptoStruct archiveert de `KXDOGE` Dogecoin range-serie met volledige Level-2 orderbook updates en trades. De publiek beschreven dekking omvat februari–september 2026. Voor de recentste 30 captured days rapporteert de site ongeveer:

- 436 trades/day;
- $5.4K turnover/day;
- 8.05c turnover-weighted spread;
- circa $540 top-of-book notional per side;
- ongeveer 1.1M L2 updates/day.

Dit maakt historische execution-realistische replay voor de **range-leg** praktisch mogelijk. De overeenkomstige threshold-serie moet nog met dezelfde timestampkwaliteit worden gevonden/verkregen voordat een cross-series historical replay geldig is.

Bron:
- https://cryptostruct.com/prediction-markets/kalshi-kxdoge

## Drie-invalshoekencheck

### 1. Semantiek / rules

**PARTIAL PASS.**

- Same-source 60-second CF Benchmarks settlementmechanisme is primair gedocumenteerd.
- Comparatorsemantiek `above`, `at least`, `between` is primair gedocumenteerd.
- De standard binary payout floor en common no-data branch zijn coherent.
- Volledige contingency/Rule 6.3(c)-robustheid is nog niet bewezen.

### 2. Formeel / adversarial counterexample search

**PASS voor standaard binary settlement.**

De relation gebruikt alleen set-inclusie en disjointness. Kleine boundary-gaps vernietigen de floor niet. De vijf relevante stateklassen leveren payout 2 of 3, nooit lager dan 2.

Falsification:
- reject pair als H niet exact subset van A is;
- reject pair als R niet exact subset van A is;
- reject pair als H en R kunnen overlappen;
- reject pair bij asset/index/date/time/source mismatch;
- reject pair als exception branch de drie legs asymmetrisch/fractioneel kan laten settelen zonder bewezen lower bound.

### 3. Execution

**DISCOVERY POSITIVE / EXECUTION NOT PROVEN.**

- Publieke displays tonen voldoende grove prijsruimte om de lane te rechtvaardigen.
- Maar de drie prijzen zijn niet uit één simultane Kalshi L2 snapshot gehaald.
- Quantity/depth per leg op hetzelfde timestamp ontbreekt.
- Slippage en cross-leg skew ontbreken.
- Daarom blijft economic status `NO_PROVEN_EDGE`.

## Vereiste volgende gate

Prospectieve scanner op de lokale Strix:

1. bind same settlement key `(asset, CF index, date, time, rule version)`;
2. canonicalize alle threshold/range predicates;
3. genereer triples `(A_low, H_high, R_between)` waarvoor `H subset A`, `R subset A`, `H intersect R = empty`;
4. subscribe op simultaneous sequence-valid L2 voor alle drie legs;
5. bereken per candidate quantity exact rounded fees per actuele fee state;
6. bereken `net_floor(q) = 2*q - executable_debit(q) - fees(q) - slippage_buffer - legging_buffer`;
7. bereken absolute locked dollars, capacity en capital-time return;
8. log opportunity lifetime op 100ms/250ms/500ms/1s/2s/5s;
9. fail closed bij sequence gap, rules drift of contingency uncertainty.

## Hardwarefit

Deze lane past redelijk goed bij ROG Strix + Starlink:

- slechts drie legs;
- algebra is triviaal en kan over veel assets/strikes lokaal worden geïndexeerd;
- crypto events zijn kortdurend, dus beperkt capital lock;
- beschikbare historische L2 voor ten minste de range-series maakt falsificatie/replay mogelijk;
- de lane vereist geen voorspelling van DOGE/BTC/ETH-richting.

Het zwakke punt blijft cross-leg execution/latency. Daarom moet de scanner opportunity lifetime meten voordat micro-live ooit wordt overwogen.

## Status

**STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**.

Dit is momenteel een hogere-prioriteit follow-up dan kleine 1–2c theoretical identities, omdat de waargenomen discovery-gap in sommige current-ish displays groot genoeg is om normale fee-orde mogelijk te overleven. Geen real-money of execution claim totdat simultaneous L2 + contingency gate + materiality pass zijn bewezen.
