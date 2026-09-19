# Crypto cross-representation — execution data context

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / DATA PATH IDENTIFIED / NO_PROVEN_EDGE**

## Doel

De grootste blocker voor `CRYPTO_RANGE_THRESHOLD_ROBUST_FLOOR_2026-09-19.md` is simultane, sequence-valid orderbookdata voor de range- én thresholdlegs. Deze notitie legt vast welke execution-data routes op 2026-09-19 zijn gevonden en welke claims nog niet bewezen zijn.

## 1. Kalshi market-maker coverage is relevant voor beide DOGE series

Kalshi's actuele Help Center over het Market Maker Program zegt dat designated market makers consistent, two-sided liquidity moeten leveren om aan hun quoting/volume obligations te voldoen.

In de actuele Covered Products-tabel staan expliciet:

- `KXDOGE` — `98% of each 1h increment`;
- `KXDOGED` — `98% of each 1h increment`.

Bron:
- https://help.kalshi.com/en/articles/13823819-how-to-become-a-market-maker-on-kalshi

Interpretatie:

- positief als **execution-context**: beide productfamilies zitten in een expliciet market-maker coverage regime;
- géén bewijs dat een specifieke strike op ieder moment voldoende size heeft;
- géén bewijs dat spreads klein zijn;
- géén bewijs van een cross-representation price gap;
- de 98%-vermelding mag niet worden vertaald naar 98% fill probability of gegarandeerde depth.

## 2. CryptoStruct — range L2 bewezen beschikbaar

CryptoStruct documenteert volledige tick-by-tick trades en full Level-2 orderbook updates voor `KXDOGE` (Dogecoin range), met dekking februari–september 2026.

Bron:
- https://cryptostruct.com/prediction-markets/kalshi-kxdoge

Dit is bruikbaar voor:

- range-leg historical replay;
- spread/depth/lifetime distributions;
- fill/slippage simulation;
- sequence/timestamp research binnen de range series.

Blocker:

- een publiek geïndexeerde `KXDOGED` threshold-pagina/tape bij CryptoStruct is tijdens deze search niet gevonden;
- daarom is een cross-series replay op basis van CryptoStruct alleen nog niet compleet.

## 3. DepthFeed — tweede historische L2-route gevonden

DepthFeed documenteert een Kalshi historical orderbook API met full yes/no depth voor crypto contracts. De docs beschrijven:

- Kalshi coverage over 21 crypto series voor 7 assets;
- 15-minute plus strike-based hourly/daily/weekly families;
- market discovery via `/v3/kalshi/markets`;
- historical orderbook snapshots per exact venue-native ticker via `/v3/kalshi/{ticker}/snapshots`;
- current full book via `/v3/kalshi/{ticker}/orderbook/latest`;
- forward-captured tick/orderbook history, met coverage die per series en capturestart varieert;
- Kalshi tick capture vanaf 2026-08-07 voor de beschreven tape, met own sequence numbers waar beschikbaar.

Bronnen:
- https://kalshipricedata.com/docs
- https://kalshipricedata.com/
- https://github.com/vcorp-dev/kalshi-price-data

Belangrijk:

DepthFeed geeft een concreet **data acquisition path** om te testen of zowel `KXDOGE` als `KXDOGED` op overlappende historische timestamps zijn vastgelegd. De documentatie toont een `KXHYPED` strike-market als Kalshi-voorbeeld en zegt dat strike-based crypto families worden gecaptured.

Maar:

- de exacte DOGE range+threshold pair coverage voor de gewenste dagen is in deze sessie nog niet via de API geverifieerd;
- API-history vereist een account/API-key en plan-window;
- docs waarschuwen dat coverage een rolling subset is en nearest-expiry markets worden geprioriteerd;
- dus `DATA PATH IDENTIFIED` is correct, niet `MATCHING TAPE PROVEN`.

## 4. Official Kalshi historical limitation

Kalshi's eigen live orderbook is uitstekend voor prospectieve capture, maar historische full-L2 kan niet betrouwbaar achteraf worden gereconstrueerd als het niet live is opgenomen. Derde partijen zoals DepthFeed/CryptoStruct bestaan juist om forward-captured history te bewaren.

Daarom blijft de voorkeursvolgorde:

1. **prospectief eigen L2 opnemen** op Strix voor alle gegenereerde A/H/R triples;
2. parallel een historische third-party replay gebruiken als falsificatie/bootstrapping;
3. nooit candle/last trade/midpoint als historische fill vervangen wanneer L2 ontbreekt.

## 5. Concrete volgende datatest

Voor DOGE:

1. ontdek via venue/API de exact matchende tickers voor event `KXDOGED-26SEP1917` en `KXDOGE-26SEP1917`;
2. query historical provider market catalogue rond 2026-09-19;
3. vereis dat alle drie legs van een triple overlappende timestampcoverage hebben;
4. ASOF-align alleen binnen een vooraf vastgelegde maximale skew;
5. reject windows met sequence/capture gaps;
6. walk full depth voor dezelfde requested quantity;
7. bereken exacte rounded Kalshi fees;
8. log `gross_floor_gap`, `net_floor_gap`, `capacity`, `lifetime`, `capital_lock`.

## 6. Geen shortcut via historische UI

PMIP/SimpleFunctions/CoinRithm/Coinbase kunnen rules/tickers/discovery helpen bevestigen, maar hun snapshots/Chance/last-price historie is niet geschikt als fillbewijs.

Een historische kandidaat wordt alleen execution-positive wanneer simultaneous/ASOF-bounded full book data de benodigde size op alle legs ondersteunt.

## Status

**RESEARCH_POSITIVE voor data availability path.**

- Range historical L2: bewezen beschikbaar bij CryptoStruct.
- Cross-series Kalshi crypto historical L2 provider: geïdentificeerd via DepthFeed.
- Exact same-event DOGE triple historical coverage: **nog niet geverifieerd**.
- Economic status: **NO_PROVEN_EDGE**.
