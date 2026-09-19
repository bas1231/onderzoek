# Index threshold ↔ range cross-representation — S&P 500 / Nasdaq-100

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Kernhypothese

Kalshi noteert voor S&P 500 en Nasdaq-100 op hetzelfde meetmoment zowel:

- threshold-contracten (`X above L`, `X above U`), en
- range-contracten (`X between L and U`).

Als underlying, meetmoment, source/transformation, comparator en settlement-domain exact aansluiten, kan een range payoff synthetisch worden gereproduceerd uit twee thresholds.

Voor indicatoren:

`A = 1[X >= L]`

`B = 1[X >= U]`, met `L < U`

`R = 1[L <= X < U]`

zou dan gelden:

`R = A - B`.

Daaruit volgt bijvoorbeeld de locked-floor portfolio:

`YES(A) + NO(B) + NO(R)`

met payoff:

`A + (1-B) + (1-R) = 2`

in iedere settlementstate, **maar alleen indien `R = A-B` exact formeel bewezen is**.

Dit is dezelfde cashflowklasse als eerder bij threshold/exact CPI, maar potentieel economisch gunstiger door korte looptijden en lagere indexfees.

---

## Primaire contractsemantiek

### S&P 500

Actuele `$INX` contract terms beschrijven:

- Underlying: prijs van de S&P 500 Index op/voor een gespecificeerd tijdstip en datum;
- Source Agency: Kalshi;
- payout criterion kan `above`, `below` of `between` zijn;
- een `between`-contract omvat Expiration Values groter dan of gelijk aan de lower bound en kleiner dan of gelijk aan de upper bound;
- `<time>` wordt in ET gespecificeerd en kan tot seconden/milliseconds worden gedefinieerd;
- minimum contract tick $0.001.

Bron:
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/INXMINMAX.pdf

### Nasdaq-100

Actuele `NASDAQ100` contract terms beschrijven dezelfde algemene structuur:

- Underlying: prijs van de Nasdaq-100 Index op/voor een gespecificeerd tijdstip en datum;
- Source Agency: Kalshi;
- payout criterion kan `above`, `below` of `between` zijn;
- `between` is inclusive op beide genoemde grenzen;
- `<value>` strikes mogen in increments van 0.0001 worden genoteerd;
- minimum contract tick $0.001.

Bron:
- https://kalshi-public-docs.s3.amazonaws.com/contract_terms/NASDAQ100.pdf

Dit ondersteunt dat threshold- en rangeproducten uit dezelfde onderliggende contractfamilie kunnen voortkomen. Het bewijst nog niet automatisch dat iedere concrete UI-range exact gelijk is aan het verschil van twee concrete thresholds.

---

## Onafhankelijke product-coexistence check

### S&P 500

Kalshi had op **7 augustus 2026 om 4pm EDT** tegelijk:

- threshold-event: `KXINXU-26AUG07H1600` — “S&P price on Aug 7, 2026 at 4pm EDT?”
- range-event: `KXINX-26AUG07H1600` — “S&P price range on Aug 7, 2026 at 4pm EDT?”

Primaire markturls:
- https://kalshi.com/markets/kx/m/kxinxu-26aug07h1600
- https://kalshi.com/markets/kx/m/kxinx-26aug07h1600

### Nasdaq-100

Kalshi had op **24 juli 2026 om 4pm EDT** tegelijk:

- threshold-event: `KXNASDAQ100U-26JUL24H1600`
- range-event: `KXNASDAQ100-26JUL24H1600`

De thresholdpagina toont onder meer `28,100 or above`, `28,110 or above`, `28,120 or above`; de rangepagina bevat onder meer `28,000 to 28,099.99`, `28,100 to 28,199.99`, `28,200 to 28,299.99`.

Primaire markturls:
- https://kalshi.com/markets/kx/test/kxnasdaq100u-26jul24h1600
- https://kalshi.com/markets/kx/m/kxnasdaq100-26jul24h1600

Dit is `RESEARCH_POSITIVE`: verschillende productrepresentaties bestaan aantoonbaar naast elkaar voor dezelfde genoemde index en hetzelfde genoemde tijdstip.

---

## Belangrijke boundary/domain-valkuil

**Niet automatisch aannemen dat een weergegeven range exact het verschil van twee thresholds is.**

Voorbeelden uit actuele/historische pagina's:

- Nasdaq ranges tonen bijvoorbeeld `28,100 to 28,199.99`;
- S&P ranges tonen bijvoorbeeld `7,550 to 7,574.9999`.

Bronnen:
- https://kalshi.com/markets/kxnasdaq100/nasdaq-range
- https://kalshi.com/markets/kxinx/sp-500-range/kxinx-26sep18h1600

De formele identity vereist bewijs dat er geen mogelijke Expiration Value bestaat in een eventuele boundary-gap tussen de range-upper-bound en de volgende threshold.

Bijvoorbeeld: als range `28,100 <= X <= 28,199.99` is en threshold `X >= 28,200`, dan is `R = A-B` alleen automatisch exact wanneer de toegestane settlement-domain geen waarde zoals `28,199.995` kan aannemen of de concrete comparator/rule anderszins de gap uitsluit.

De `NASDAQ100` contract terms staan strike-levels op increments van 0.0001 toe; dat veld bewijst op zichzelf niet dat de **Expiration Value** slechts op een 0.01-grid kan liggen. Daarom blijft discrete-domain/precision proof verplicht.

**Agentregel:** een mooie UI-aansluiting van boundaries is discovery, geen theorem proof.

---

## Fee-/capital-efficiency voordeel

De Kalshi fee schedule specificeert voor S&P 500 en Nasdaq-100 event markets een lagere feeformule dan de algemene event-contractfee:

`fee = round_up(0.035 * C * P * (1-P))`

Bronnen:
- https://kalshi.com/docs/kalshi-fee-schedule.pdf
- https://kalshi.com/regulatory/fee-schedule

Kalshi biedt daarnaast dagelijkse/intraday indexcontracten, waardoor capital lock veel korter kan zijn dan bij langlopende GDP/year-end partitions.

Dit maakt deze cross-representation lane economisch interessanter **als** een executable cross werkelijk voorkomt.

Runtime blijft altijd actuele series/event fee-state autoritatief; geen statische hardcode zonder fee-change check.

---

## Drie-invalshoekencheck

### Hoek 1 — primaire semantiek/productstructuur

**PASS voor structural candidate.**

De primaire contract terms ondersteunen één index-underlying met `above/below/between` payoutvormen. Historische primaire Kalshi-marktpagina's bevestigen threshold- en range-events op hetzelfde genoemde 4pm-moment.

### Hoek 2 — formele algebra / counterexample search

**CONDITIONAL PASS / DOMAIN PROOF MISSING.**

De identity `R=A-B` is algebraïsch exact wanneer:

- dezelfde underlying/source/transformation geldt;
- dezelfde measurement timestamp geldt;
- lower/upper comparators exact aansluiten;
- geen toegestane settlementwaarde in een boundary-gap kan vallen;
- uitzonderings-/no-data-/reviewbranches de relatieve payoff niet verbreken.

Zonder settlement-domain/precision proof moet de verifier de relation status op `DOMAIN_UNPROVEN` zetten, niet op `PROVED_IDENTITY`.

### Hoek 3 — actuele execution

**NOT PROVEN.**

Deze ronde heeft geen simultane point-in-time L2-snapshot van een concrete threshold-low + threshold-high + range-triplet vastgelegd. Web/UI `Chance`, last price of gecachte marktkaarten tellen niet als execution evidence.

Geen `net_locked_edge > 0` bewezen.

Economic status: `NO_PROVEN_EDGE`.

---

## Required data voor promotie

Per concrete candidate-triplet:

1. exact `rules_primary` / `rules_secondary` voor alle drie markten;
2. canonical underlying identifier;
3. exact measurement timestamp en timezone;
4. source agency + transformation/fallback/no-data branch;
5. exact comparator (`>`, `>=`, `<`, `<=`, inclusive between);
6. settlement-value precision/domain proof;
7. simultane L2 voor de drie legs, inclusief sizes;
8. actuele fee type/multiplier/waiver state;
9. cross-leg timestamp skew;
10. partial-fill/legging model;
11. `net_locked_edge`, capacity, absolute dollars en capital-time return.

---

## Falsificatie

Verwerp een pair/triplet onmiddellijk wanneer:

- source, timestamp of underlying verschilt;
- range en threshold boundaries niet exact exhaustief aansluiten;
- domain/precision onbekend is en een theoretische gap mogelijk blijft;
- no-data/fallback/review rules de identity kunnen verbreken;
- fee-net executable cost >= payoff floor;
- depth onvoldoende is voor materiële absolute profit;
- positieve states prospectief alleen korter leven dan conservatief haalbare retail/Starlink latency.

---

## Scannerarchitectuur

Canonicaliseer ieder indexcontract naar minimaal:

`(underlying, measurement_timestamp, source, transformation, comparator, lower_bound, upper_bound, exception_signature)`

Daarna:

1. indexeer threshold-contracten per canonical settlement key;
2. indexeer range-contracten op dezelfde key;
3. zoek range boundaries met bijpassende threshold boundaries;
4. voer domain/precision proof uit;
5. genereer alleen bij proof de payout identity;
6. haal simultaneous L2;
7. bereken all-taker net_locked_edge;
8. indien all-taker negatief maar gross dichtbij positief: evalueer apart `maker-trigger -> bounded completion`;
9. rangschik op absolute locked dollars, return per capital day, capacity en opportunity lifetime.

Deze search is computation-heavy maar geschikt voor lokale i9-hardware; alleen de laatste executiongate is latencygevoelig.

---

## Onderzoeksconclusie

**Nieuwe structurele lane bevestigd:** S&P/Nasdaq threshold- en rangeproducten bestaan aantoonbaar als verschillende representaties rond dezelfde onderliggende index/tijd.

**Niet bewezen:** dat concrete range boundaries altijd exact synthetiseerbaar zijn, of dat er momenteel een fee-net executable cross bestaat.

De belangrijkste volgende proof-vraag is niet prijs maar **settlement-domain precision**. Pas daarna verdient een live L2 scanner voor concrete 3-leg identities theorem-proof status.
