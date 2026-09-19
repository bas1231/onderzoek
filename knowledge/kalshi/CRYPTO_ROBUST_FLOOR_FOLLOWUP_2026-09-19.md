# Crypto robust floor — contingency + historical L2 follow-up

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / NO_PROVEN_EDGE**

Deze notitie vult `CRYPTO_RANGE_THRESHOLD_ROBUST_FLOOR_2026-09-19.md` en `CRYPTO_XREP_EXECUTION_DATA_CONTEXT_2026-09-19.md` aan.

## 1. Exacte contingencytekst uit actuele CRYPTO terms

De actuele CRYPTO contract terms zijn visueel en tekstueel gecontroleerd. De relevante passages zeggen:

- standaard payout criterion gebruikt de opgegeven crypto/index/date/time;
- bij geen of onvolledige data op expiration time resolven affected strikes naar No;
- Settlement Date kan opschuiven wanneer Market Outcome Review plaatsvindt;
- onder `Contingencies` mag Kalshi vóór settlement de Market Outcome Review Process starten met een verwijzing naar `Rule 6.3(d)`;
- als een Expiration Value niet kan worden bepaald, zegt de contracttekst dat Kalshi payouts mag bepalen pursuant to `Rule 6.3(b)`.

Bron:
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/RIPPLE.pdf

## 2. Rulebook-numbering mismatch = fail-closed

De actuele zoekbare Kalshi Rulebook v1.24-weergave beschrijft:

- Rule 6.3(a): standaard Binary Contract settlement;
- Rule 6.3(b): Scalar Contract settlement;
- Rule 6.3(c): discretionaire payout/interpretation wanneer Expiration Value/scope/proportion niet kan worden bepaald.

Daarmee sluit de nummering niet schoon aan op de verwijzingen in de bekeken CRYPTO terms.

Dit mag **niet** door een agent worden gerepareerd met de aanname dat “ze vast dezelfde clausule bedoelen”.

Agentregel:

- standard binary branch: relation mag worden bewezen;
- explicit common no-data -> all affected strikes No: floor mag worden bewezen wanneer dezelfde data failure alle legs raakt;
- iedere andere contingency/Outcome Review branch: `CONTINGENCY_UNPROVEN`, fail closed voor unconditional arbitrage claim.

Bron:
- https://kalshi-public-docs.s3.amazonaws.com/regulatory/rulebook/Kalshi%20Rulebook%20v1.24.pdf

## 3. Market-maker coverage ondersteunt execution-prioriteit, niet de edge

Kalshi's Market Maker Program-documentatie zegt dat designated market makers consistente two-sided liquidity moeten leveren onder quoting/volume requirements.

De actuele covered-products tabel vermeldt expliciet:

- `KXDOGE` — 98% of each 1h increment;
- `KXDOGED` — 98% of each 1h increment.

Bron:
- https://help.kalshi.com/en/articles/13823819-how-to-become-a-market-maker-on-kalshi

Interpretatie:

- positief: beide kanten van de gewenste range↔threshold relation zijn expliciet covered products;
- niet afleiden: 98% fill probability, gegarandeerde depth, specifieke spread, of fee-net cross.

## 4. Matching historical L2 path is nu concreter

Naast CryptoStruct voor `KXDOGE` range is DepthFeed gevonden als mogelijke cross-series historische L2-bron.

DepthFeed documenteert voor Kalshi:

- 21 crypto series over 7 assets;
- strike-based crypto market families met hourly/daily/weekly windows;
- market discovery via `/v3/kalshi/markets`;
- newest full yes/no book per exact ticker;
- historical orderbook snapshots per exact ticker;
- tick capture vanaf 2026-08-07 voor de beschreven Kalshi tape;
- rolling/nearest-expiry coverage, dus niet ieder market object is gegarandeerd aanwezig;
- sequence-valid capture metadata op de tick surface waar beschikbaar.

Bron:
- https://kalshipricedata.com/docs

Deze docs tonen bijvoorbeeld `KXHYPED-...-T...` als strike-market example en zeggen dat de 21-series crypto coverage expanded is. Dat maakt een matching DOGE threshold+range replay **plausibel en direct testbaar**, maar exact `KXDOGE-26SEP...` + `KXDOGED-26SEP...` overlap is nog niet API-verifieerd in deze sessie.

Nieuwe status van de historische blocker:

- vóór deze follow-up: `MATCHING_THRESHOLD_TAPE_SOURCE_NOT_FOUND`;
- nu: `CANDIDATE_CROSS_SERIES_L2_PROVIDER_FOUND`;
- nog vereist: `EXACT_TICKER_COVERAGE_VERIFIED`.

## 5. Waarom dit praktisch belangrijk is

Als DepthFeed beide exact matching legs/triples op dezelfde tijdvensters heeft, kunnen we zonder weken prospectief wachten een eerste execution-realistische replay uitvoeren:

1. discover exact venue-native tickers;
2. haal A_low, H_high en R books voor dezelfde event/time;
3. align op receive timestamp met vooraf vaste skewlimiet;
4. reject gaps;
5. walk depth voor q=1,5,10,25,50,100...;
6. exact rounded fee per fill shard;
7. meet `net_floor(q)` en max positive capacity;
8. meet opportunity lifetime;
9. cluster per economische event zodat 100 ticks niet als 100 onafhankelijke kansen tellen.

## 6. Current research verdict

De nieuwe crypto-floor lane blijft de meest interessante execution-first kandidaat uit deze researchronde, maar de juiste status blijft:

**STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**.

Verbetering sinds vorige notitie:

- contingency blocker is specifieker en wordt expliciet fail-closed behandeld;
- zowel KXDOGE als KXDOGED blijken market-maker covered products;
- een mogelijke cross-series historical full-L2 provider is gevonden;
- daarmee is de volgende stap geen nieuw theoretisch onderzoek maar **exact pair coverage verifiëren + replay of prospectieve capture**.
