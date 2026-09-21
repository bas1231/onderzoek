# WX-TWC-CANONICALIZATION-E024

Date: 2026-09-21
Status: RESEARCH FOUNDATION
Economic conclusion: NO_PROVEN_EDGE
Safety: no live trading, no paid actions, no wallet actions, no OpenAI API

## Verified current public-source requirements

Kalshi's current Weather Markets documentation says:

- Hourly temperature markets settle on readings from The Weather Company (TWC).
- The target is the temperature at the exact named time.
- The target is tied to the station coordinates named in the market rules; Kalshi gives KORD for Chicago as an example.
- TWC's reported value is official/final for these contracts.
- Preliminary TWC readings can differ from the final reported value because of rounding/conversion.
- Settlement typically processes about 25–35 minutes after market close.
- Historical readings/outcome data are exposed through weather.com/kalshi.
- Each market's own rules remain authoritative for its official settlement source.

Kalshi also states more generally that the contract terms define the information source used for outcome determination. Live-data graphs may lag or differ from the verification source and therefore are not settlement authority by themselves.

## Canonical target key

No observation is eligible for Weather Runner modelling unless a point-in-time record can construct the following target key without guessing:

`venue | market_id | rules_version_or_hash | station_coordinates_or_explicit_station_id | settlement_local_datetime | timezone | settlement_source=TWC | comparator_or_bucket`

Multiple thresholds/buckets tied to one underlying hourly TWC observation must share the same settlement-event identifier and must not be treated as independent targets.

## Fail-closed exclusions

Exclude a market/observation from signal evaluation when any of these are unresolved:

- station or coordinates inferred only from city name;
- timezone inferred rather than explicit/derivable from authoritative market metadata;
- exact named settlement time missing;
- settlement source not locked from contemporaneous market rules;
- preliminary TWC value substituted for final target;
- live-data graph assumed to equal the official settlement feed;
- rules captured only after the prediction timestamp without point-in-time provenance.

## Black-box boundary

Do not infer the internal TWC rounding, conversion, interpolation, station-merging or revision algorithm unless primary evidence explicitly documents it. Public TWC observations may be used as predictors, but are not assumed identical to Kalshi's settlement feed.

## Next decisive evidence

Capture at least one current contract from each active hourly-weather series with immutable series/event/market rule snapshots and demonstrate that the canonical target key above can be populated point-in-time. Only then should Phase 0A signal comparisons use those contracts.

## Sources

- https://help.kalshi.com/en/articles/13823837-weather-markets
- https://help.kalshi.com/en/articles/13823826-market-outcomes
- https://help.kalshi.com/en/articles/13823831-live-data-graphs
