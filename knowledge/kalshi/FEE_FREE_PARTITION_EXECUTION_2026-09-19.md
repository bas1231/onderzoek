# Fee-free partitions & deadline dominance — execution-first research

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / NO_PROVEN_EDGE**

## Waarom deze lane

Normale Kalshi-takerfees en spreads vernietigen veel kleine bruto payout-identiteiten. Daarom is een aparte scan over **fee-free series** logisch: dezelfde formele cashflow kan daar economisch relevant worden bij veel kleinere prijsafwijkingen.

De primaire bron blijft actuele Kalshi series metadata (`fee_multiplier`) en point-in-time market data. Een oude PDF of secundaire fee-lijst is alleen discovery; fee-state moet bij iedere kandidaat opnieuw worden gebonden.

Kalshi API-documentatie exposeert `fee_multiplier` op seriesniveau en executable marketvelden zoals yes/no bid/ask en sizes.

Bronnen:
- https://docs.kalshi.com/api-reference/market/get-series
- https://docs.kalshi.com/api-reference/market/get-markets
- https://docs.kalshi.com/api-reference/exchange/get-series-fee-changes

## Lane A — exhaustive mutually-exclusive partitions

Als `N` uitkomsten exact onderling uitsluitend én collectief exhaustief zijn, geldt:

- buy-all-YES settlement = `$1`;
- buy-all-NO settlement = `$(N-1)`.

Executionvoorwaarden:

`sum(YES asks) + all_costs < 100c`

of equivalent voor de andere richting:

`sum(NO asks) + all_costs < (N-1)*100c`.

UI `Chance`, midpoint, last trade en derdepartij-odds mogen niet als basket cost worden gebruikt.

### BTC EOY control

`KXBTCY-27JAN0100` is een 28-bucket Bitcoin year-end range event en de actuele Kalshi market page vermeldt expliciet `No fees`. Recente Kalshi-weergaven tonen o.a. centrale buckets rond 11–15c YES en een hoge totale volume-orde.

Primaire bron:
- https://kalshi.com/markets/kxbtcy/btc-price-range-eoy/kxbtcy-27jan0100

Een onafhankelijke execution-scanner rapporteerde voor een volledige fee-free snapshot:

- `KXBTCY-27JAN0100`: basket cost 105.10c, dus +5.10c boven par;
- `KXETHY-27JAN0100`: 106.00c, +6.00c boven par.

Dus geen execution-positive candidate in die snapshot.

## Onafhankelijke exchange-wide bevestiging: below-par baskets bestaan

Een onafhankelijke scanner (`aimarketscanner.cloud`) rapporteerde een volledige sweep van ~81k Kalshi-markten en 13 geverifieerde fee-free partitions. Twee partitions stonden daadwerkelijk **onder par**:

- `KXGDPYEAR-28`: 99c voor $1 payout, capacity 5 complete baskets, annualized ~0.40%; bruto absolute edge slechts ~$0.05.
- `KXGDPYEAR-36`: 99c voor $1 payout, capacity 71 complete baskets, annualized ~0.09%; bruto absolute edge slechts ~$0.71.

De scanner onderdrukte beide alerts omdat `capacity × edge` onder een $25 materialiteitsvloer bleef.

Bron:
- https://aimarketscanner.cloud/

Dit is belangrijk bewijs dat execution-first below-par baskets **werkelijk kunnen voorkomen**, maar ook dat een formeel positieve arbitrage economisch praktisch waardeloos kan zijn door te weinig depth, te kleine absolute dollars of zeer lange capital lock.

### Current-state falsification

Latere/current-ish views van dezelfde GDP-partitions staan niet stabiel onder par. Een actuele Kalshi 2028 page toont centrale YES asks zoals 13c, 12c en 13c; een recente volledige 2036 mirror/snapshot zat ongeveer op 104c totaal voor 14 YES-buckets. Daarmee is de historische 99c toestand niet structureel persistent.

Een derdepartij-board voor GDP-2029 leek op basis van `Chance`-velden zelfs maar ~78% totaal te tonen. Controle tegen Kalshi's echte displayed asks liet echter zien dat de asks veel hoger waren (bijvoorbeeld centrale strikes met chance 6/16/5 maar asks rond 14/20/13). Dit is een expliciete falsificatie van `sum(chance)<100 => arb`.

Agentregel: **alleen simultaneous asks/bids + sizes tellen als execution evidence**.

## Lane B — fee-free deadline dominance (klein-N, twee legs)

Voor hetzelfde event met deadlines `t1 < t2` geldt:

`E(t1) ⊂ E(t2)`.

Daarom heeft portfolio:

`NO(event by t1) + YES(event by t2)`

settlementcashflow:

- event vóór t1: `0 + 1 = 1`;
- event tussen t1 en t2: `1 + 1 = 2`;
- event niet vóór t2: `1 + 0 = 1`.

Dus de payout floor is exact `$1` zonder kansmodel.

Een execution-positive candidate bestaat wanneer:

`ask_NO_early + ask_YES_late + all_costs < 100c`.

Dit is infrastructureel aantrekkelijker dan 14–28-leg baskets: slechts twee legs, minder legging risk, en geen HFT-infrastructuur nodig als de dislocatie lang genoeg leeft.

### Actuele controles

`KXGREENLAND` staat in de fee-free lijst van het 7-juli-2026 schema. Recente Kalshi pages tonen bijvoorbeeld:

- vroegere deadline `Before 2027`: NO ongeveer 96–96.3c;
- latere deadline `Before Jan 20, 2029`: YES ongeveer 19c.

Som ~115c, dus ruim boven de $1 floor: **geen candidate**.

Een tweede verwante Greenland deadline event liet eveneens een combinatie ruim boven par zien.

Bronnen:
- https://kalshi.com/markets/kxgreenland/greenland-purchase/kxgreenland-29
- Kalshi fee schedule / current series metadata moet voor execution opnieuw worden geverifieerd.

`KXGAMBLINGREPEAL` is eveneens historisch fee-free en heeft meerdere deadlines. Een recente derdepartij-orderbook snapshot gaf ongeveer:

- Before 2027: YES 16 / NO 86
- Before Apr 1 2027: YES 27 / NO 76
- Before Sep 1 2027: YES 32 / NO 71
- Before Jan 1 2028: YES 47 / NO 56

Nested floorparen kosten daar bijvoorbeeld 86+27=113c en 76+32=108c: geen candidate.

Bron (secondary execution snapshot; altijd herverifiëren tegen Kalshi):
- https://pmip.io/markets/kalshi/KXGAMBLINGREPEAL-26JAN-27

## Drie-invalshoekencheck

### 1. Formele/payoff-invalshoek — PASS

- Exhaustive partition identities zijn direct algebraïsch.
- Deadline dominance is direct set-theoretisch: `E(t1) subset E(t2)`.
- Geen forecast of probability model nodig.

### 2. Onafhankelijke/historische invalshoek — RESEARCH_POSITIVE

- Onafhankelijke exchange-wide scanner registreerde daadwerkelijk twee fee-free partitions op 99c voor $1 payout.
- Deze waren klein/traag maar tonen dat below-par execution snapshots niet louter theoretisch zijn.
- Current-ish rechecks tonen dat de toestand niet persistent is.

### 3. Live/economische execution — NO_PROVEN_EDGE

- Actueel gecontroleerde fee-free BTC/ETH/Greenland/deadline voorbeelden zijn niet below par.
- Historisch GDP 99c had onvoldoende absolute profit/capital efficiency.
- Geen eigen simultane prospective L2 capture in deze researchpass.

Economische status blijft daarom `NO_PROVEN_EDGE`.

## Nieuwe materialiteitsgate

`net_locked_edge > 0` is noodzakelijk maar niet voldoende.

Agents/scanners moeten ook berekenen:

- `executable_capacity_contracts`
- `absolute_locked_profit_usd = net_locked_edge_per_contract * executable_capacity_contracts`
- `capital_locked_usd`
- `days_to_expected_cash_release`
- `return_on_locked_capital`
- `annualized_or_return_per_capital_day`

Een 1c edge met vijf contracts en jaren capital lock krijgt veel lagere prioriteit dan een vergelijkbare floor met korte settlement, dikke depth en herhaalbaarheid.

## Scannerprioriteit voor Strix + Starlink

Hoge prioriteit:

1. `fee_multiplier == 0` of bewezen lage fee;
2. 2–5 legs vóór 14–28 legs;
3. deterministische payout floor;
4. korte/middellange capital lock;
5. voldoende top-of-book/L2 capacity;
6. candidate lifetime lang genoeg voor retail latency/jitter;
7. absolute profit boven een vooraf ingestelde materialiteitsvloer.

Lage prioriteit:

- `Chance`-underrounds zonder asks;
- 1c edges met een paar contracts;
- multi-year lock met sub-1% annualized return;
- baskets met tientallen legs wanneer dezelfde economics met 2–5 legs kan worden gevonden;
- opportunities die alleen op millisecondenniveau bestaan.

## Prospectieve test die nu nodig is

Bouw/gebruik een read-only scanner die iedere sweep:

1. actuele series fee metadata bindt;
2. event partitions en nested deadline-relaties canonicaliseert;
3. simultaneous executable asks/bids + size verzamelt;
4. complete basket capacity op minimum leg depth berekent;
5. fees/slippage/skewbuffer toepast;
6. `net_locked_edge`, absolute dollars en return/capital-day berekent;
7. alleen candidates bewaart die alle gates halen;
8. alle near-misses logt om de edge-distance-distributie te meten.

Doel is niet veel alerts, maar bewijs of **economisch materiële, retail-uitvoerbare locked cashflows** prospectief terugkeren.
