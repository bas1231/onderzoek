# Live Momentum Dashboard

Datum: 2026-09-19
Status: **METHODOLOGY — RESEARCH/OBSERVABILITY — NO_PROVEN_EDGE**

## Doel

Bouw een venue-onafhankelijk realtime dashboard dat markten toont waar publieke handelsactiviteit en/of prijsbeweging uitzonderlijk snel versnelt. Het dashboard is primair observability + discovery-infrastructuur voor behavioral/FOMO, informed-flow, news-response en liquidity-shock hypotheses. Een ranking of alert is nooit zelfstandig een trading-signaal.

## Harde architectuurregel: geen dashboard-polling als primaire bron

Het dashboard mag niet per browser-refresh of widget opnieuw venue-API's pollen.

Voorkeursarchitectuur:

`venue websocket / streaming feed -> één lokale collector -> immutable raw -> normalized event bus/state -> feature engine -> dashboard`

De research-engine en dashboard consumeren dezelfde lokale feed. REST wordt alleen gebruikt voor bootstrap/snapshot, metadata, herstel na sequence gaps, of venues zonder bruikbare realtime stream.

Hierdoor kost het dashboard zelf praktisch geen extra venue-polls wanneer de benodigde realtime feed al wordt verzameld.

## Venue adapters

Elke venue-adapter publiceert waar beschikbaar een gestandaardiseerde eventvorm:

```yaml
venue: polymarket
market_id: ...
ts_source: ...
ts_received: ...
event_type: trade|ticker|book_delta|book_snapshot|lifecycle
price: ...
quantity: ...
notional: ...
side_or_direction: ...
direction_authority: authoritative|inferred|unknown
best_bid: ...
best_ask: ...
bid_depth: ...
ask_depth: ...
sequence: ...
```

Geen venue-semantiek verzinnen. Wanneer aggressor/maker/taker direction niet autoritatief bekend is, wordt die feature als `UNKNOWN` of `INFERRED` gemarkeerd en nooit als harde waarheid gebruikt.

## Wat betekent 'extreem snel stijgende bets'?

Niet één ruwe volume-teller. We gebruiken meerdere onafhankelijke korte-horizonfeatures.

### Activiteitsversnelling

- trade count 5s / 30s / 2m;
- notional volume 5s / 30s / 2m;
- volume acceleration ten opzichte van eigen recente baseline;
- unique trade bursts waar de feed dat betrouwbaar ondersteunt;
- inter-arrival-time collapse.

### Prijsversnelling

- absolute prijsverandering 5s / 30s / 2m;
- velocity en acceleration;
- distance vanaf 5m/30m local anchor;
- round-number / threshold crossing.

### Orderbook stress

- spread compression/widening;
- depth depletion;
- bid/ask replenishment;
- top-of-book turnover;
- imbalance wanneer direction betrouwbaar is;
- cancel-vs-trade decomposition waar data dit toelaat.

### Context

- volume/open-interest/liquidity regime;
- time-to-close;
- category;
- related-market movement;
- public-news/source update flag;
- cross-venue synchronization;
- informed-flow-risk flag.

## Momentum / Attention score

Het dashboard mag een research-ranking tonen zoals:

`attention_score = robust_z(volume_accel) + robust_z(trade_rate_accel) + robust_z(abs_price_velocity) + robust_z(depth_depletion)`

Dit is nadrukkelijk **geen voorspelling van richting of winstgevendheid**.

Gebruik robust rolling baselines per `venue × market/regime` in plaats van één globale threshold, omdat 100 contracten in een illiquide markt extreem kan zijn en in een grote markt triviaal.

Alle componenten en thresholds worden versieerbaar opgeslagen. Geen post-hoc tuning op P&L zonder nieuw experiment.

## Dashboard views

### 1. HOT NOW

Topmarkten op attention/momentum score met:

- venue;
- market/event;
- huidige executable bid/ask;
- price move 10s / 1m / 5m;
- volume/notional 10s / 1m / 5m;
- relative activity z-score;
- depth change;
- time-to-close;
- data trust badge;
- reason codes.

### 2. FLOW SHOCKS

Markten met plotselinge trade-rate/volume/depth shocks.

### 3. PRICE SHOCKS

Snelste prijsbewegingen, onafhankelijk van richting.

### 4. BEHAVIORAL CANDIDATES

Hoge behavioral pressure maar lage/medium informed-flow-risk. Alleen discovery; nooit auto-trade op basis van dashboardscore.

### 5. INFORMED-FLOW WARNING

Nieuws/source update, cross-venue synchronized move, depth withdrawal, abnormal trade size of snelle adverse continuation. Deze view helpt voorkomen dat FOMO wordt verward met beter geïnformeerde orderflow.

### 6. CROSS-VENUE

Mogelijk dezelfde gebeurtenis/wereldstate op verschillende venues met relatieve beweging, timestamp uncertainty en semantic-match confidence.

### 7. DATA HEALTH

Collector health, websocket disconnects, sequence gaps, stale feeds, clock skew/uncertainty, API backoff/rate-limit state en invalid books.

## Alerting

Alerts worden lokaal gegenereerd op features, niet door extra REST-polls.

Voorbeeld reason codes:

- `TRADE_RATE_99P`
- `VOLUME_ACCEL_99P`
- `PRICE_MOVE_5M_99P`
- `DEPTH_COLLAPSE`
- `CROSS_VENUE_SYNC`
- `BEHAVIORAL_PRESSURE_HIGH`
- `INFORMED_FLOW_RISK_HIGH`

Alerts worden gededuped/cooldowned zodat één markt niet continu spam veroorzaakt.

## REST-budgetdiscipline

REST is fallback/metadata, niet de dashboard-loop.

Regels:

1. subscribe/stream waar mogelijk;
2. bootstrap één snapshot en pas daarna deltas toe;
3. alleen snapshot opnieuw bij reconnect/sequence gap;
4. metadata lokaal cachen met venue-specifieke TTL;
5. adaptive polling voor venues zonder stream: actieve/hot markten sneller, koude markten veel langzamer;
6. centrale per-venue token/rate-limit governor;
7. dashboard leest nooit rechtstreeks van venue REST;
8. API-budget en throttle-events worden gemeten en zichtbaar gemaakt.

## Opslag

Niet iedere afgeleide score hoeft permanent als raw event te worden opgeslagen. Bewaar:

- immutable venue events/raw manifests;
- normalized trades/book state;
- feature-version;
- triggered alerts/candidates;
- rolling aggregates voor snelle UI;
- experiment-relevante snapshots.

## Researchwaarde

Het dashboard is nuttig omdat dezelfde data direct meerdere hypotheses voedt:

- FOMO/herding reversal of continuation;
- surprise under/overreaction;
- informed-vs-noise flow;
- momentum decay;
- liquidity withdrawal;
- cross-venue information propagation;
- behavioral salience;
- regime-conditioned execution.

Daarmee is dit geen losse UI-feature maar observability van de kernresearch.

## Build priority

Dit hoeft niet vóór de collector te bestaan. Bouwvolgorde:

1. venue adapter + collector;
2. normalized event schema;
3. rolling feature engine;
4. local query/state API;
5. minimal dashboard (`HOT NOW` + `DATA HEALTH`);
6. behavioral/informed-flow panels;
7. cross-venue panel;
8. pas daarna visuele verfijning.

De eerste dashboardversie moet klein blijven en vooral bewijzen dat dezelfde stream zonder extra polling bruikbaar is voor realtime discovery.

## Economische status

Een snel stijgende markt is alleen een `OBSERVATION` / discovery candidate. Momentum, volume explosion of FOMO is geen bewezen edge. Promotie blijft onderworpen aan de volledige Pre-Build Killer, drie kill reviews, replay, validation, untouched holdout en prospective shadow.