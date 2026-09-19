# Short-horizon reduced-fee index algebra

Datum: 2026-09-19
Status: **STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Hypothese

S&P 500- en Nasdaq-100-contractfamilies zijn interessant voor execution-first research omdat ze tegelijk:

- veel korte looptijden hebben (daily/weekly/intraday);
- threshold- en range-structuren aanbieden;
- volgens de actuele/publieke fee schedule-bronnen een lagere fee-coëfficiënt hebben dan de algemene event-contractfee;
- daardoor een lagere fee-hurdle en kortere capital lock kunnen hebben dan langlopende GDP/crypto-partitions.

Dit is een scanner-lane, geen bewezen edge.

## Fee-evidence

De Kalshi fee schedule voor 2026 vermeldt voor S&P 500- en Nasdaq-100-markten:

`fee = round up(0.035 * C * P * (1-P))`

tegenover de algemene `0.07`-coëfficiënt voor veel andere event contracts.

Bronnen:
- https://kalshi.com/regulatory/fee-schedule
- https://kalshi.com/docs/kalshi-fee-schedule.pdf
- https://help.kalshi.com/en/articles/13823805-fees

**Runtime-regel:** de scanner mag deze historische/publieke schedule nooit blind hardcoden. Gebruik actuele series/event fee-state en fee-change feeds als autoriteit.

## Structurele identities

### A. Nested threshold dominance

Voor dezelfde settlementvariabele `X` en `a < b`:

`{X >= b} subset {X >= a}`

Dus:

`YES(X >= a) + NO(X >= b) >= $1`

voor iedere toegestane settlementstate.

Executioncandidate wanneer:

`ask_yes_low + ask_no_high + all_costs < $1`

### B. Adjacent thresholds synthetiseren een range

Bij discrete/regelmatig gedefinieerde strikes kan het verschil tussen twee thresholds een interval/range representeren, MAAR alleen als comparator, rounding, settlementbron en domain exact bewijzen dat er geen ongedekte tussenstate bestaat.

Geen integer/discrete aanname zonder primaire rule/domain proof.

### C. Exhaustive range partition

Als een range-event exact mutually exclusive + exhaustive is:

`sum(all YES payouts) = $1`

maar de economics tellen alleen op simultaneous executable asks + depth.

## Actuele marktstructuur

De actuele Kalshi financiële categorie toont onder meer:

- dagelijkse S&P/Nasdaq Up/Down-contracten;
- S&P/Nasdaq price-range-events met tientallen buckets;
- S&P/Nasdaq intraday threshold-ladders met veel strikes.

Bronnen:
- https://kalshi.com/category/financials/frequency/daily
- https://kalshi.com/category/financials/indices
- https://kalshi.com/markets/kxnasdaq100/nasdaq-range/kxnasdaq100-26sep21h1600

Dit bevestigt voldoende structurele breedte voor een automatische scanner.

## Adversarial falsification: UI chance is onbruikbaar als execution proof

De actuele categoriepagina liet in dezelfde S&P thresholdfamilie zichtbare `Chance`-waarden zien waarbij een hogere threshold soms hoger leek geprijsd dan een lagere threshold. Dat is strijdig met monotone event-inclusie indien deze waarden als probabilities zouden worden geïnterpreteerd.

Daaruit volgt NIET dat er arbitrage is.

Het is juist een bevestiging van de bestaande agentregel:

- geen `Chance`;
- geen midpoint;
- geen last trade;
- geen gecachte categoriekaart;

als execution evidence.

Alleen simultane L2/bid-ask + sizes uit de exchange-data tellen.

## Drie-invalshoekencheck

### 1. Formele semantiek

**PASS als structuurklasse.** Nested threshold dominance is wiskundig direct mits dezelfde settlementvariabele, comparator en rules gelden. Range/exact synthese vereist extra domain proof.

### 2. Fee/capital economics

**RESEARCH_POSITIVE.** De gepubliceerde lagere fee-coëfficiënt en korte looptijden maken de hurdle aantoonbaar gunstiger dan standaard-fee, langlopende baskets. Kortere expiry vermindert capital lock.

### 3. Actuele execution

**NOT PROVEN.** De huidige publieke webweergaven zijn onvoldoende om simultane L2/depth over volledige ladders te bewijzen. Sommige zichtbare upcoming range-events hadden bovendien zeer weinig volume. Geen fee-net positieve laddercross is in deze ronde bewezen.

Economic status blijft `NO_PROVEN_EDGE`.

## Scannerontwerp

Prioriteit per event:

1. bind exact series/event/market rules en settlement source;
2. bind actuele fee-state;
3. sorteer thresholds canoniek op strike/comparator;
4. genereer alleen logisch bewezen nested pairs;
5. haal multiple orderbooks in één zo strak mogelijke point-in-time batch;
6. bereken executable quantity op beide legs;
7. bereken fee met echte rounding voor target quantity;
8. trek slippage/latency/legging buffer af;
9. bereken `net_locked_edge`, `absolute_locked_profit_usd` en `return_per_capital_day`;
10. archiveer ook near-misses om de edge-distance distribution te leren.

## Waarom passend bij Strix + Starlink

Deze lane is computation-heavy maar niet intrinsiek HFT-only:

- veel thresholds kunnen lokaal op de i9 worden gecanonicaliseerd en gepaard;
- formele relation search is goedkoop na indexing;
- korte expiry verbetert capital efficiency;
- alleen echte crosses hoeven latencykritisch behandeld te worden.

Kill/deprioritize wanneer prospectief blijkt dat positieve crosses uitsluitend korter bestaan dan conservatief haalbare retail-latency of structureel te weinig depth hebben.

## Volgende test

Bouw/gebruik een read-only prospective scanner voor minimaal:

- S&P daily/intraday thresholds;
- Nasdaq daily/intraday thresholds;
- S&P/Nasdaq range partitions;

met volledige point-in-time fee provenance en L2.

Rapporteer per kandidaat:

`gross_floor_gap -> fee-adjusted gap -> executable depth -> absolute dollars -> capital-time return -> lifetime_ms`

Pas daarna beoordelen of deze lane micro-live verdient.
