# Negative evidence ledger

Doel: voorkomen dat mensen of agents gefalsificeerde/zwakke ideeën later opnieuw als verse edge presenteren. Een entry wordt niet verwijderd wanneer het idee niet werkte; nieuw bewijs wordt als nieuwe versie toegevoegd.

## Kalshi — duidelijke negatives / gesloten routes

### Simple soccer 3-way partition
Minstens 12 actuele regulation-time examples handmatig gecontroleerd; zichtbare HOME+DRAW+AWAY YES-baskets ongeveer 101–105 cent vóór fees voor 100 cent payout. Geen simpele arb in deze spot-check.

Bron: `bas1231/market_algebra`, `docs/NEGATIVE_EVIDENCE.md`.

### BTC duplicate-title / >100k false positive
Vergelijkbare titels/bron/einddatum bleken verschillende measurement start windows en strike-semantiek te hebben. Geen identity. Les: title matching is alleen discovery.

Bron: `bas1231/predictionbot`, `onderzoek/KALSHI_COMPLEX_STRATEGY_HUNT_2026-09-19.md`.

### BTC race ↔ annual minimum
Aantrekkelijke logische relatie faalde als riskless relation door verschillende settlement-transformaties/measurement rules.

Bron: idem.

### Solana ladder mirror anomaly
Externe mirror suggereerde tijdelijk arbitrage; actuele Kalshi buy-prijzen maakten de combinatie >$1. Geclassificeerd als stale/mid/mirror artefact.

Bron: idem.

### Hourly weather ↔ daily high/low deterministic identity
Afgewezen voor de onderzochte families omdat settlement sources verschilden (TWC versus NWS).

Bron: idem.

### Team total / game total / spread eerste examples
Formele identities bestaan, maar eerste gecontroleerde examples waren ruim te duur. Een 3-leg score-cover voorbeeld kostte ongeveer 152 cent vóór fees voor een minimum payout van 100 cent.

Status: identity geldig; economische edge niet aangetoond.

### Nested qualifier first checks
Golf en SEC placement ladders waren in gecontroleerde actuele examples economisch correct genest; geen dominance arb. Sommige UI/chance tiles leken inconsistent maar bleken geen executable asks.

### KXHIGHNY integer-domain shortcut
`UNPROVEN_DISCRETE_DOMAIN`. Geen integer-gap logic gebruiken zonder source-domain proof.

Bron: `bas1231/proof-hunter`, PH-E009.

### KXHIGHNY six-NO unconditional settlement guarantee
Formeel gesloten in PH-E012. Standard-path conditional floor bestond, maar no-data/last-fair-price en Market Outcome Review exception classes verhinderden unconditional pre-settlement guarantee.

Status: `TESTED_NEGATIVE / ROUTE_CLOSED`.

### Collateral return = gratis cash
Afgewezen model. Collateral return/netting verandert available-funds/collateral accounting en position value. Een structural offset mag niet als extra wealth of withdrawable profit worden geboekt zonder daadwerkelijke accounting proof.

### Live-sports raw score crossing = final settlement lock
Afgewezen als generieke regel. VAR/replay/challengeprocedures kunnen scoring state herzien. Vereist sport-specifieke finality en daarna afzonderlijke contract-settlement proof.

### Live Watcher positive pricing observations
Eerste census: 3 confirmations met positieve net lower bound, maar alle drie `SETTLEMENT_UNPROVEN`. Geen market edge.

### Legacy lifecycle/finality reconstruction
Niet toegestaan. Pre-LW0015/LW0017 evidence mist contemporaneous detail; latere brondata mag dit niet invullen.

### Scheduled macro first-decidability after official release
Afgewezen voor de gecontroleerde Fed/CPI/payroll-families als simpele strategie `wacht op officiële release → handel daarna op stale Kalshi quote`. De gecontroleerde markten sloten vóór de geplande officiële release: FOMC ongeveer één minuut ervoor; CPI/payrolls ongeveer één tot vijf minuten ervoor afhankelijk van contract. Er is dus in deze families geen post-release executable Kalshi-window om te exploiteren.

Status: `TESTED_NEGATIVE` voor deze geplande macrofamilies. Dit sluit first-decidability in andere contractfamilies niet uit.

Bron: `knowledge/kalshi/priority_followups_2026-09-19.yaml`, `KAL-DEC-MACRO-001`; Federal Reserve/BLS primaire release-timing plus gedateerde Kalshi API snapshots.

## ForecastEx / andere venues

### ForecastEx same-market YES+NO coupon farming
Afgewezen. Rule 604 net offsetting same-market positions; daarnaast vond een publieke 12.4M-snapshot census in het onderzochte corpus geen combined asks onder $1 en minimum $1.03.

### Predict.fun deterministic yield loop
Afgewezen. Split/merge retourneert principal; yield is afzonderlijk, variabel en extern gegenereerd via DeFi lending. Geen deterministic >1 split-hold-merge cycle.

### Limitless state-dependent conversion cycle
Geen nieuwe value-creating cycle gevonden. Split/merge/NegRisk/redeem reduceerden tot static payoff identities of redemption/capital timing.

### Opinion state-dependent conversion cycle
Geen proof-safe value-creating cycle gevonden. Matched trade kan bovendien nog on-chain falen.

### Trueo reward hedge — huidige factory
Mechanisme theoretisch interessant, maar onderzochte factory zette rewardAmount=0. Huidige concrete reward-route daardoor niet economisch actief.

## Runner/Strix historical research

### Focused Runner entry screening
Historische high-coverage screening promoveerde geen entry candidates. Fees/slippage/failures/latency/self-impact waren bovendien niet inbegrepen en nieuwste historische holdout bleef ongeopend. Geen economic PnL claim.

### Early sell / absorption
Sommige scores verhoogden de frequentie van extreme winner labels, maar in zichtbare top-selecties bleven gemiddelde, mediane, winsorized en leave-top-k PnL-statistieken negatief. Dit is development evidence en geen pristine confirmation.

## Algemene anti-patterns

- `theoretische identity == edge` — fout;
- `beter model == market edge` — fout;
- `midpoint/last trade/UI chance == executable price` — fout;
- `maker zijn == edge` — fout; adverse selection/fills/inventory tellen;
- `favorite-longshot bias == direct trading rule` — onvoldoende;
- `parlay/combo overpricing is bekend == onze edge` — onvoldoende;
- `zelfde titel == zelfde contract` — fout;
- `score threshold gekruist == settlement final` — fout;
- `historisch positief zonder contemporaneous L2 == executable replay` — fout;
- `kleine gross cross == netto profit` — vaak fout door fees/depth/legging;
- criteria post-hoc versoepelen nadat een gate faalt — verboden.

Economische default blijft **NO_PROVEN_EDGE**.
