# Index range → threshold dominance — two-leg locked-floor lane

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Waarom deze lane sterker is dan exacte threshold-range synthese

De aparte cross-representation research liet zien dat een exacte identity zoals:

`range[L,U) = threshold[X>=L] - threshold[X>=U]`

kan vastlopen op settlement-domain / boundary precision.

Voor **dominance** is die volledige equality niet nodig.

Als een concrete range `R` volledig binnen een concrete lower-threshold event `A` valt, dan geldt simpelweg:

`R subset A`.

Daaruit volgt voor iedere settlementstate:

`YES(A) + NO(R) = A + (1-R) >= 1`.

Dit geeft een **twee-leg gegarandeerde payout-floor van $1** wanneer de subsetrelatie semantisch bewezen is.

De upper boundary van de range hoeft hiervoor niet exact tegen een tweede threshold aan te sluiten. Daardoor vervalt een belangrijke precision/gap-failure mode.

---

## Concrete productstructuur

Historische primaire Kalshi-pagina's tonen voor Nasdaq-100 op **24 juli 2026 om 4pm EDT** tegelijkertijd:

- threshold event `KXNASDAQ100U-26JUL24H1600`, met strikes zoals `28,100 or above`, `28,110 or above`, `28,120 or above`;
- range event `KXNASDAQ100-26JUL24H1600`, met ranges zoals `28,100 to 28,199.99`.

Bronnen:
- https://kalshi.com/markets/kx/test/kxnasdaq100u-26jul24h1600
- https://kalshi.com/markets/kx/m/kxnasdaq100-26jul24h1600

Voor S&P 500 bestaan op dezelfde manier threshold- en range-events rond dezelfde genoemde meetmomenten, bijvoorbeeld op 7 augustus 2026 om 4pm EDT:

- `KXINXU-26AUG07H1600`
- `KXINX-26AUG07H1600`

Bronnen:
- https://kalshi.com/markets/kx/m/kxinxu-26aug07h1600
- https://kalshi.com/markets/kx/m/kxinx-26aug07h1600

De actuele algemene contract terms voor `$INX` en `NASDAQ100` ondersteunen payoutvormen `above/below/between` rond dezelfde index-underlyingfamilie.

Bronnen:
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/INXMINMAX.pdf
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/NASDAQ100.pdf

---

## Formele relation

Laat:

- `R` de concrete range-outcome zijn;
- `A` de concrete threshold-outcome zijn;
- de canonical contract parser bewijzen dat `R => A` voor iedere toegestane Expiration Value en iedere relevante exception branch.

Dan:

`R <= A`.

En dus:

`A + (1-R) >= 1`.

Een executioncandidate bestaat alleen wanneer:

`ask_yes(A) + ask_no(R) + fees + slippage_buffer + execution_risk_buffer < $1`.

De candidate quantity is begrensd door de werkelijk beschikbare simultaneous depth op **beide** legs.

---

## Waarom dit goed past bij Strix + Starlink

Vergeleken met grote exhaustive baskets:

- slechts **2 legs**;
- formele set-inclusie is lokaal zeer goedkoop te bewijzen;
- S&P/Nasdaq-contracten hebben een historisch/gepubliceerd verlaagd fee-regime ten opzichte van de algemene fee;
- daily/intraday expiries beperken capital lock;
- er hoeft geen probabilistisch model te worden geschat;
- er is geen noodzaak om tientallen legs binnen een paar milliseconden tegelijk te raken.

De executionstap blijft latencygevoelig maar is veel realistischer voor retail-infrastructuur dan 14-28 leg baskets of pure HFT races.

---

## Fee-evidence

De gepubliceerde fee schedule specificeert voor S&P 500 / Nasdaq-100 event-contracten:

`fee = round_up(0.035 * C * P * (1-P))`.

Bron:
- https://kalshi.com/docs/kalshi-fee-schedule.pdf

Runtime-regel blijft: bind de actuele fee-state point-in-time; gebruik series/event fee changes en overrides en hardcode geen oud tarief als autoriteit.

---

## Drie-invalshoekencheck

### 1. Product-/semantiekhoek

**PASS ALS STRUCTURELE KLASSE, CONCRETE PAIR MOET NOG WORDEN GEBONDEN.**

Threshold- en rangeproducten voor dezelfde genoemde index/timestamp bestaan aantoonbaar. De exacte subsetrelatie moet per concrete pair worden bewezen uit actuele rules, comparator en exception signature.

### 2. Formele/adversarial hoek

**PASS voor iedere pair waar `R => A` formeel wordt bewezen.**

Belangrijk voordeel: een onbekende settlementprecision bovenaan de range verbreekt deze lower-threshold subset niet. De earlier equality-lane kan daardoor `DOMAIN_UNPROVEN` blijven terwijl dominance al wel bewijsbaar kan zijn.

Adversarial counterexamples die nog steeds moeten worden uitgesloten:

- threshold lower comparator is strikt en range bevat exact de grenswaarde;
- source/transformation verschilt;
- measurement timestamps verschillen;
- no-data/fallback/market-review branch laat de twee contracten anders settelen;
- een concrete market rule wijkt af van de generieke seriessemantiek.

### 3. Executionhoek

**NOT PROVEN.**

De huidige webweergave levert geen simultane point-in-time L2 voor matching threshold/range pairs. Categorie-`Chance`, last trades of gecachte webquotes gelden niet als executionbewijs.

Geen actuele fee-net `net_locked_edge > 0` bewezen.

Economic status: `NO_PROVEN_EDGE`.

---

## Actuele researchcontrol

Actuele Nasdaq-rangeevents bestaan nog steeds, bijvoorbeeld `KXNASDAQ100-26SEP21H1600`, met ranges zoals `28,100 to 28,199.99`.

Bron:
- https://kalshi.com/markets/kxnasdaq100/nasdaq-range/kxnasdaq100-26sep21h1600

De actuele financiële/indices catalogus toont tegelijk omvangrijke intraday threshold-ladders voor S&P en Nasdaq. De webcatalogus kan echter niet betrouwbaar worden gebruikt voor relation pricing omdat zichtbare `Chance`-velden niet noodzakelijk simultane executable quotes zijn.

Bron:
- https://kalshi.com/category/financials/indices

Dit is voldoende voor scanner-discovery, niet voor economic promotion.

---

## Scannerlogica

Canonical pair key:

`(underlying, exact_measurement_timestamp, source, transformation, exception_signature)`

Voor iedere range `R=[L,U]`:

1. zoek lower-thresholds `A` binnen dezelfde canonical key;
2. laat de theorem layer bewijzen of `R => A`;
3. genereer alleen bewezen dominance pairs;
4. haal beide orderbooks zo simultaan mogelijk;
5. gebruik `YES ask(A)` en `NO ask(R)` plus depth;
6. bereken echte fees inclusief rounding;
7. bereken conservative net_locked_edge;
8. bereken executable capacity, absolute locked dollars en return per capital day;
9. log near-misses en opportunity lifetime;
10. indien all-taker bijna positief is, evalueer apart maker-trigger -> bounded completion.

## Mogelijke spiegelrelaties

Andere setrelaties kunnen automatisch uit dezelfde AST volgen, bijvoorbeeld:

- `R subset A` -> `YES(A)+NO(R) >= 1`;
- als `R` formeel disjoint is met event `B`, dan `NO(R)+NO(B) >= 1`;
- als `A subset R`, dan `YES(R)+NO(A) >= 1`.

Geen specifieke formule hardcoden wanneer dezelfde relation-engine generiek set-inclusion/disjointness kan bewijzen.

---

## Onderzoeksconclusie

**Nieuwe lane:** twee-leg dominance tussen range- en thresholdrepresentaties van dezelfde index/timestamp.

Deze lane is robuuster dan exacte range-synthese omdat zij alleen set-inclusie nodig heeft en daardoor een deel van het settlement-precisionprobleem omzeilt.

**Nog niet aangetoond:** een actuele executable pair onder par na fees/depth/buffers.

De juiste volgende gate is prospectieve simultaneous L2 capture over canonical matching S&P/Nasdaq range-threshold pairs.
