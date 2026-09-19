# Informed-flow shadowing & toxicity — public-data research lane

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Onderzoeksvraag

Kunnen publiek observeerbare handelsfootprints van waarschijnlijk beter geïnformeerde traders worden gebruikt om een execution-realistische edge te vinden, zonder individuen te deanonymiseren, niet-openbare informatie te verkrijgen of blind whales te kopiëren?

De veilige en bruikbare formulering is:

> Detecteer **informed/toxic flow regimes** uit publieke trades + orderbooks, en gebruik die informatie om (a) adverse selection te vermijden en/of (b) formeel gerelateerde markten te vinden die trager repricen.

Noem een live trader niet feitelijk een "insider" op basis van marktdata alleen. Dezelfde footprint kan ontstaan door superieure analyse, snellere publieke informatieverwerking, hedging, inventory management of private informatie.

---

## Hoofdbevinding

De beste route is waarschijnlijk **niet tegen werkelijk geïnformeerde flow in handelen**.

Als flow echt informatie bevat, is contrair handelen juist de kant met negatieve adverse selection. De economische kansen zijn eerder:

1. **Toxicity shield voor maker-strategieën** — trek/reprice passieve quotes wanneer waarschijnlijk geïnformeerde flow stijgt, zodat de geïnformeerde trader niet goedkoop jouw stale liquidity kan oppakken.
2. **Cross-market informed-flow oracle** — gebruik de eerste markt waarin geïnformeerde flow zichtbaar wordt als publiek signaal en zoek naar formeel gerelateerde contracten die nog niet volledig hebben gereageerd.
3. **Delayed same-market follow-the-leader** — alleen testen wanneer de post-trade price discovery historisch lang genoeg blijft bestaan om na retail-latency en fees nog waarde te hebben.
4. **Contrarian fade** — lage prioriteit; alleen toegestaan als prospectieve data aantonen dat de impact tijdelijk/manipulatief is en systematisch mean-revert. Niet aannemen dat grote flow manipulatie is.

Voor de lokale ROG Strix + Starlink setup krijgt route 1 en 2 de hoogste prioriteit. Pure milliseconde-copytrading krijgt lage prioriteit.

---

## Bewijs — invalshoek 1: Kalshi informed-flow / adverse-selection literatuur

### Kalshi Mentions: abnormal trade size

Ellis Delvecchio (2026), `Informed Trading in Prediction Markets: Evidence from Kalshi Mentions Contracts`, analyseert >2.000 settled Kalshi-contracten op elf volume-horizons.

De publieke abstract rapporteert:

- `Abnormal Trade Size (ATS)` voorspelt de uiteindelijke contractuitkomst significant, ook na controle voor prijs, volume, spread en category fixed effects;
- voorspellende kracht neemt toe richting resolutie;
- ATS-spikes zijn persistent: **73.5% transition probability** tussen opeenvolgende horizons;
- een `follow-the-leader` strategie op mid-life horizons genereerde in die studie **positieve netto returns na transactiekosten**.

Bron:
- https://scholarship.claremont.edu/cmc_theses/4166/

Beperking: volledige thesis is restricted; alleen de publieke abstract kan hier als evidence worden gebruikt. Dit is geen bewijs dat hetzelfde effect in andere Kalshi-categorieën of huidige regimes blijft bestaan.

### Kalshi 41.6M trades: one-sided toxicity

Bartlett & O'Hara (2026), `Adverse Selection in Prediction Markets: Evidence from Kalshi`, gebruikt **41.6 miljoen trades**.

Publiek gerapporteerde hoofdbevindingen:

- single-name contracts hebben meer informed price impact dan broad-based contracts;
- een aangepaste VPIN/toxicitymaat laat zien dat **one-sided order flow maker losses voorspelt in single-name markets**, maar niet hetzelfde patroon in broad-based markets;
- makers worden dus juist kwetsbaar wanneer zij passieve liquidity aanbieden tegen toxic/informed flow.

Bronnen:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6615739
- https://gideon-bornstein.com/si2026.html

Dit ondersteunt vooral de **toxicity shield** lane, niet blind follow-the-whale.

---

## Bewijs — invalshoek 2: Polymarket concentrated informed trading

Cheong & Tamayo (2026), `Beyond the Wisdom of the Crowd: Concentrated Informed Trading in Earnings Prediction Markets`, vindt in Polymarket earnings markets dat een kleine groep grote traders substantieel nauwkeuriger is dan overige deelnemers. Hun voordeel blijft volgens de abstract bestaan wanneer zij tegen recente orderflow in handelen en is consistent met strategisch informed trading.

Bron:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6685139

Dit ondersteunt de hypothese dat **grootte + richting + timing + marktcontext** informatief kunnen zijn.

Maar grootte alleen is geen voldoende classifier.

Akey, Grégoire, Harvie & Martineau (2026) analyseren **588 miljoen Polymarket trades / $67B volume**. Zij vinden dat de top 1% van winstgevende gebruikers 76.5% van de profits vangt, maar dat succesvolle traders vooral liquidity providers zijn; hun analyse suggereert dat insider trading **niet** de hoofdverklaring is voor de grootste structurele winnaars.

Bronnen:
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6443103
- https://cepr.org/index.php/publications/dp21615

Dus:

> `whale == insider` is fout.

Een systeem moet **informed-flow probability** schatten, niet simpel alle grote trades volgen.

---

## Bewijs — invalshoek 3: adversarial falsificatie van "insider trackers"

Een publieke Polymarket anomaly study (`Finding the Needle`) analyseerde 7.655 wallets, $113.5M large-trade value en 1.337 markets. De studie is nuttig als falsificatievoorbeeld:

- zonder liquidity filter kwamen alle top-50 anomaly scores uit zeer kleine markten; het signaal was praktisch onbruikbaar;
- de geselecteerde watchlist had hogere buy-side resolution accuracy, maar 85% van de buy-value kwam van één wallet;
- de 2-day markoutverbetering was slechts ongeveer **15.3 bps versus baseline**, economisch klein ten opzichte van normale prediction-market fricties;
- geen formele significantietests waren uitgevoerd.

Bron:
- https://www.iykykmarkets.io/research/articles/blind_universe_research_article.html

Daarnaast laat population-scale Information Leakage Score research zien dat resolution semantics een zeer grote blocker zijn: slechts **88 van 12.708** onderzochte candidate markets leverden een berekenbare score en slechts 1 van 32 documented-case markets viel in scope.

Bronnen:
- https://arxiv.org/abs/2605.00459
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6686819

Conclusie:

- geen wallet-ranking als trading edge zonder echte markout/executiontest;
- liquiditeitsfilter is verplicht;
- contractsemantiek en event timing moeten vooraf correct zijn;
- outcome accuracy alleen is onvoldoende — **entry-price EV en forward markout** tellen.

---

## Venue-data: Kalshi is hiervoor technisch geschikt

Kalshi's officiële public-trades WebSocket geeft per executed trade onder meer:

- `market_ticker`;
- `yes_price_dollars` / `no_price_dollars`;
- `count_fp`;
- `taker_side`;
- `is_block_trade`;
- `ts` en milliseconde `ts_ms`.

Bron:
- https://docs.kalshi.com/websockets/public-trades

Kalshi's authenticated orderbook WebSocket geeft:

- sequence-numbered snapshot;
- sequence-numbered deltas;
- side, price, quantity change;
- `ts_ms`.

Bron:
- https://docs.kalshi.com/websockets/orderbook-updates

Dus op Kalshi hoeven we geen walletidentiteit te kennen. Voor dit onderzoek is **flow-level toxicity** genoeg.

---

# Voorgestelde Informed Flow Score (IFS)

Geen vaste gewichten vooraf als waarheid aannemen. Eerst features preregistreren, daarna trainen/valideren.

Per `(economic_event, contract, rolling_window)`:

### 1. Abnormal Trade Size

Meet hoe uitzonderlijk agressieve trade-size is ten opzichte van vergelijkbare trades in dezelfde markt/regime.

Bijvoorbeeld:

`ATS_z = zscore(log(aggressive_trade_size) | price_bucket, spread, volume, time_to_close, category)`

Belangrijk: conditioneer op liquidity/price; een trade van 1.000 contracts is niet overal even abnormaal.

### 2. Signed aggressive-flow imbalance

`imbalance = (YES_taker_volume - NO_taker_volume) / (YES_taker_volume + NO_taker_volume)`

Meet op meerdere windows, bijvoorbeeld:

- 1s;
- 5s;
- 30s;
- 2m;
- 10m.

### 3. Flow persistence

Sterker wanneer meerdere onafhankelijke trade-bursts dezelfde richting houden.

Niet simpel trade count gebruiken wanneer één groot order in meerdere prints wordt gefragmenteerd.

### 4. Immediate markout / toxicity

Historisch:

`markout_h = signed_direction * (mid[t+h] - execution_price)`

voor bijvoorbeeld:

- 1s;
- 5s;
- 30s;
- 2m;
- 5m.

Als agressieve orders consistent direct gunstige markout hebben, waren makers aan de andere kant waarschijnlijk adverse-selected.

### 5. Book reaction

Waarschuwingsfeatures:

- depth withdrawal aan de oude prijs;
- spread widening;
- same-direction best bid/ask walk;
- herhaalde offers die worden opgegeten zonder reversion.

### 6. Cross-contract confirmation

Sterkere informed-flow hypothese wanneer logisch gerelateerde markets **coherent dezelfde informatie verwerken**.

Voorbeelden:

- threshold ladders;
- exact/range/threshold representaties;
- primitives versus MVE/combo;
- dezelfde gebeurtenis met verschillende deadlines;
- cross-venue exact-equivalent markets.

### 7. Public-information veto / regime label

Markeer of rond de flow al een bekende publieke source update/news shock plaatsvond.

Dit label is nodig om achteraf niet `fast public-information processing` ten onrechte als insider flow te noemen.

Voor trading hoeft dit signaal niet waardeloos te zijn, maar latency/competition is dan waarschijnlijk veel hoger.

---

# Strategie A — Toxicity Shield

## Hypothese

Wanneer IFS/toxicity hoog is, is passief quoten tegen de informed direction negatief EV. Door quotes tijdelijk terug te trekken, te verbreden of richting de flow te repricen, vermijden we de transfer naar geïnformeerde takers.

Dit is de meest direct door Bartlett/O'Hara ondersteunde lane.

## Test

Vergelijk identieke candidate maker quotes:

- baseline: altijd quoten;
- shield: niet quoten wanneer `IFS > pre_registered_threshold`;
- skew: fair value/quote richting flow aanpassen.

Meet:

- fill rate;
- maker PnL na fees;
- 1s/5s/30s markout;
- settlement PnL;
- missed spread capture;
- tail losses.

### Succescriterium

Shield moet op untouched/prospective data **net expectancy of downside verbeteren** na rekening met gemiste fills.

Geen succesclaim wanneer het alleen minder handelt en daardoor toevallig minder verliest.

---

# Strategie B — Cross-Market Informed-Flow Oracle

## Hypothese

Een informed/toxic trade in markt `A` kan de eerste publieke prijsinformatie zijn. Wanneer formeel gerelateerde markt `B` trager reageert, is `A` een publiek oracle voor `B`.

Dit is interessanter dan dezelfde whale achterna kopen, omdat de whale zelf juist de beste liquidity in `A` kan hebben opgegeten.

## Voorbeeldarchitectuur

1. Grote/persistente YES-taker flow verschijnt in een high threshold.
2. IFS wordt hoog en immediate markout bevestigt persistence.
3. Relation graph zoekt alle contracts die door de informatie geraakt zouden moeten worden:
   - lagere thresholds;
   - ranges;
   - exact buckets;
   - combos waarin de primitive zit;
   - semantisch equivalente cross-venue contracten.
4. Alleen wanneer `B` nog een execution-aware residual heeft na bid/ask, fees, depth en minimaal retail-latency wordt een candidate gelogd.

## Belangrijk

Gebruik formele payoff-relaties waar mogelijk. Een probabilistisch verband mag niet als harde identity worden behandeld.

### Te meten propagation delays

Voor iedere informed-flow trigger:

- 100 ms;
- 250 ms;
- 500 ms;
- 1 s;
- 2 s;
- 5 s;
- 30 s;
- 2 min.

Voor Strix + Starlink is een effect dat vrijwel altijd vóór 500ms verdwijnt laag-prioriteit. Een residual dat regelmatig 2–30 seconden of langer overleeft is veel interessanter.

---

# Strategie C — Delayed Follow-the-Leader

Kalshi Mentions evidence maakt deze lane testwaardig, maar niet generiek bewezen.

Trigger pas na bevestiging, bijvoorbeeld:

- ATS hoog;
- zelfde richting persistent over meerdere windows;
- book reprices permanent in plaats van direct terug te vallen;
- geen extreme spread/depth collapse die entry onuitvoerbaar maakt.

Entry mag alleen wanneer:

`expected_remaining_information_move - executable_spread - fee - slippage_buffer > 0`

Test vertragingen van 250ms t/m minuten.

Kill de lane als de volledige prijsimpact al in de eerste print zit of als follower-entry systematisch slechtere prijs krijgt dan de resterende markout waard is.

---

# Strategie D — Contrarian / manipulation fade

**Lage prioriteit.**

Alleen activeren wanneer prospectieve data bewijzen dat een specifieke flowklasse:

- grote initiële price impact heeft;
- géén cross-market bevestiging krijgt;
- book depth terugkeert;
- prijs binnen vooraf gedefinieerde horizon systematisch mean-revert;
- na fees/slippage nog positief is.

Niet gebruiken op basis van de aanname `grote trade = whale = manipulatie`.

Prediction-market literatuur laat juist zien dat informed traders prijzen permanent kunnen verbeteren en dat manipulatie niet automatisch een eenvoudige fade-edge creëert.

---

# Drie-invalshoeken testplan

## Hoek 1 — Direct informed-flow predictiveness

Historische dataset:

- trades + taker side;
- sequence-safe L2;
- settlement outcomes;
- exact fee-state;
- category/time-to-close/liquidity.

Vraag:

> Voorspelt IFS toekomstige markout en/of settlementrichting **incremental boven huidige marktprijs**?

Gebruik controls/matched samples op:

- price bucket;
- spread;
- volume/liquidity;
- category;
- time to close;
- event cluster.

Geen edge wanneer IFS alleen vertelt wat de huidige prijs al volledig bevat.

## Hoek 2 — Execution-realistische strategy replay

Replay afzonderlijk:

A. toxicity shield;
B. same-market follower;
C. cross-market follower.

Voor iedere trigger:

- bind point-in-time L2;
- delay execution met realistische 250ms/500ms/1s/2s/5s scenarios;
- gebruik depth/VWAP;
- exacte fees/rounding;
- partial-fill/legging;
- cluster dependent contracts onder één economic event.

## Hoek 3 — Prospectieve shadow/canary

Vooraf freeze:

- IFS-formule;
- thresholds;
- relation graph;
- news/source veto;
- latency assumptions;
- net-edge requirements;
- kill criteria.

Log daarna prospectief alle triggers voordat settlement/forward price bekend is.

Geen post-hoc toevoeging van een feature omdat een spectaculaire whale toevallig won.

---

# Kill criteria

De lane wordt verzwakt/gedood als één of meer van de volgende structureel optreden:

- IFS heeft geen incremental predictive value boven marktprijs + liquidity controls;
- follower-edge verdwijnt vóór 1s/realistische Starlink latency;
- follower slippage/fees consumeren de forward markout;
- cross-market residual verdwijnt zodra semantic/economic relation correct wordt gemodelleerd;
- toxicity shield verbetert alleen PnL doordat bijna alle fills worden weggefilterd, zonder betere expectancy per risk/exposure;
- effect komt alleen uit zeer illiquide micro-markets;
- wallet/whale labels leveren geen stabiele out-of-sample verbetering;
- effect is category/regime-specific en verdwijnt op untouched temporal holdout.

---

# Praktische prioriteit voor deze setup

Voor ROG Strix i9 + Starlink:

1. **Toxicity shield voor passive-maker lanes** — HIGH.
2. **Cross-market propagation after informed-flow trigger** — HIGH / meest interessante nieuwe discovery-route.
3. **Delayed same-market follow-the-leader** — MEDIUM, academisch ondersteund maar executiongevoelig.
4. **Polymarket wallet-specific whale following** — MEDIUM_LOW; wallet transparency helpt research, maar selection/slippage/hedgingconfounds zijn groot.
5. **Contrarian whale fade** — LOW totdat prospectief reversionbewijs bestaat.

De i9 kan relation graphs, rolling feature-engineering, replay en modelselectie lokaal makkelijk dragen. De netwerkbeperking betekent dat uitsluitend sub-millisecond opportunities niet de primaire target mogen zijn.

---

# Juridische/ethische researchgrens

Deze lane gebruikt uitsluitend:

- publieke trades/orderbooks;
- publieke blockchain/walletdata waar van toepassing;
- publieke news/source timestamps;
- formele marktregels.

Niet doen:

- niet-openbare informatie kopen/vragen/ontvangen;
- personen deanonymiseren;
- credential/access abuse;
- collusie/manipulatie/spoofing;
- iemand als juridisch "insider" bestempelen op basis van statistische flow alleen.

We exploiteren **publieke prijsontdekking**, niet de niet-openbare informatie zelf.

---

# Eindstatus

**RESEARCH_POSITIVE / STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**.

Sterkste bestaande evidence:

- informed/toxic flow is meetbaar op Kalshi;
- abnormal trade size kan outcome-predictive zijn;
- one-sided toxicity kan maker losses voorspellen;
- whale/informed concentration bestaat in bepaalde Polymarket subsets;
- blind whale-copying is onvoldoende ondersteund en kan door slippage/selection volledig verdwijnen.

De nieuwe, nog onbewezen kernhypothese is:

> **Gebruik informed-flow niet primair om dezelfde markt achterna te kopen, maar als public oracle voor een payoff-relation graph en zoek related markets die nog niet volledig gerepriced zijn.**

Dit moet als eerste op historische sequence-safe L2 en daarna prospectief shadow worden getest.
