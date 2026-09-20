# WS-SPORTS-OFFICIAL-DATA-MM-CROWDING-001

- observed_at: 2026-09-20T11:04:00+02:00
- source_class: PRIMARY_VENDOR + INDUSTRY_REPORTING
- venues: [Kalshi, Polymarket]
- mechanism_id: MECH-SPORTS-OFFICIAL-DATA-MM-CROWDING
- status: FACT_VERIFIED / WEAK_SIGNAL
- evidence_strength: STRONG_EMPIRICAL_FOR_MARKET_STRUCTURE, NOT_EDGE_PROOF
- legality: CLEAR
- urgency: MEDIUM_HIGH

## Finding

A new 18 September 2026 iGamingBusiness infrastructure report gives unusually concrete evidence that sports prediction-market making is professionalising quickly around official low-latency data. Catalist Sports says it supplies ITF tennis data to Kalshi and Polymarket and must also supply that data to the firms making those markets. Catalist says Kalshi initially supplied a list of fewer than 10 potential market makers; Catalist has now completed agreements with close to 20 and is engaging with roughly another 20.

Catalist's own primary announcement independently verifies the underlying infrastructure change: Kalshi receives official low-latency data used to create, manage and settle markets, plus exclusive US prediction-market live streams, covering more than 65,000 tennis matches annually. Catalist's site also advertises official point-by-point L1/L2 data.

## Why this matters

This is stronger than the generic statement that sports markets are becoming crowded. It identifies the information input used by professional liquidity providers and gives a rough count showing rapid expansion of the maker cohort. It therefore changes the prior for any sports lane whose expected advantage depends on ordinary public score feeds, streams, or basic maker spread capture.

The important economic mechanism is `official-data access -> faster/more reliable state estimate -> lower stale-quote exposure -> better maker economics -> crowding of public-data strategies`.

This does NOT prove that market making is unprofitable for a small participant. It does imply that a sports strategy should not receive engineering priority merely because it can react to live scores or quote a spread. It needs evidence of an information source, contract relation, lifecycle state, or execution niche not already commoditised by official-feed-equipped makers.

## Relation to known work

- Weakens generic sports live-score/state-lock and naive sports market-making priors.
- Supports the existing insistence on execution-realistic replay and prospective shadow tests.
- Complements Surplus Maker/adverse-selection research: maker spread is compensation for inventory and informed-flow risk, not edge by itself.
- Raises the benchmark for Pons/Runner-like sports signals: compare signal timestamps against official low-latency feed timestamps, not only public web/API timestamps.
- Does not falsify formally proven settlement-state opportunities; those may survive if semantics/finality rather than score latency is the source of edge.

## Weak-signal score (0-5)

- novelty: 4
- source_strength: 4
- mechanism_distance_from_known: 2
- plausible_economic_impact: 4
- transferability: 4
- time_sensitivity: 4
- testability: 5
- data_availability: 3
- legality: 5
- crowding_decay_risk: 5
- reproducibility: 3

## Required data / falsification

Required: timestamped official-feed observations (or a defensible proxy), venue L2/L3, fills/markouts, market-maker count/participation proxies, and matched sports/market families.

Cheap falsification: measure whether public-feed/state signals still precede executable repricing by a stable margin after fees and realistic fill assumptions. If no positive lag survives prospectively, kill the public-data sports timing lane. Separately, test whether maker returns remain positive after 1s/5s/30s markouts and inventory costs; if not, spread/rebate capture is not a benchmark edge.

## Execution blockers

Official-feed licensing/cost; unknown maker identities; queue priority; adverse selection; venue-specific fees/rebates; potentially sub-second repricing; settlement semantics; inability to reconstruct historical point-in-time official data.

## Provenance

Primary vendor: Catalist Sports, `Catalist Sports and Kalshi announce exclusive multi-sport content partnership`, announcement dated 2026-09-08: https://catalistsports.com/news/catalist-sports-and-kalshi-announce-exclusive-multi-sport-content-partnership/

Industry reporting: iGamingBusiness, Scott Longley, `The tech providers behind the prediction markets boom`, 2026-09-18: https://igamingbusiness.com/prediction-markets/tech-providers-powering-prediction-markets/

Independent corroboration of partnership/data scope: Gaming Intelligence, 2026-09-08: https://www.gamingintelligence.com/finance/235703-catalist-sports-becomes-first-streaming-partner-for-kalshi/

## Current conclusion

Research-priority update, not an edge claim. Treat generic sports public-data timing and undifferentiated maker spread capture as a harder/crowding-sensitive benchmark. NO_PROVEN_EDGE.