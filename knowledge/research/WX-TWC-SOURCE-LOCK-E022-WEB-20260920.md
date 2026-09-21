# WX-TWC-SOURCE-LOCK-E022 — web source lock

Retrieved: 2026-09-20
Status: SOURCE_EVIDENCE_CAPTURED_WEB
Economic conclusion: NO_PROVEN_EDGE
Safety: no live trading, no paid actions, no wallet actions

## Primary-source findings

1. Kalshi Weather Markets states that hourly temperature markets settle on readings from The Weather Company (TWC), while daily high/low markets use the final NWS Daily Climate Report. Each market still names its official settlement source in its own rules.
2. Kalshi states that hourly markets resolve on the temperature at the exact named time as reported by TWC for the station coordinates named in the market rules, with KORD given as an example for Chicago.
3. Kalshi states that the TWC value is official and final for hourly settlement; other weather services and NWS reports are not authoritative for these hourly contracts.
4. Kalshi explicitly warns that preliminary TWC readings may differ from the final reported value because of rounding and conversion.
5. Kalshi states that hourly settlement processes approximately 25–35 minutes after market close and points to weather.com/kalshi for historical readings/outcome data.
6. The Weather Company developer documentation exposes hourly historical conditions and time-series observations, including geocode and ICAO/IATA lookup paths. These APIs require an API key, so they are not used here as a free execution dependency.
7. TWC documentation says time-series observations can return observations from physical site-based stations, with availability depending on station reporting frequency/operational status.

## Research implications

- The modelling target must remain the final TWC hourly settlement value, not an assumed objectively true air temperature.
- Station/location canonicalisation is mandatory before signal testing: market rule station coordinates / ICAO identifier, exact settlement time, timezone, and TWC target must be stored point-in-time.
- Preliminary TWC values cannot be treated as equivalent to final settlement values. Any preliminary-to-final feature is only valid when the preliminary value was observable before market close and the historical archive preserves its original timestamp/value.
- Rounding/conversion is an explicit documented source of preliminary/final divergence, but the exact transformation/algorithm is not documented in the captured public sources and must remain black-box/unknown.
- Generic TWC APIs prove that TWC has hourly and site-based observation products, but they do not by themselves prove that a particular API response is exactly the Kalshi settlement feed. Contract-specific evidence remains required.

## Explicit unknowns / blockers

- Exact internal TWC algorithm used to produce the final Kalshi settlement value.
- Exact relationship between weather.com/kalshi values and public TWC developer API products.
- Contract-by-contract station/coordinate mapping for all active hourly markets.
- Whether any preliminary value is exposed early enough, with immutable timestamp provenance, to be a legitimate pre-close predictor.
- Exact rounding/conversion sequence used before the final hourly settlement value is published.

## Source URLs

- https://help.kalshi.com/en/articles/13823837-weather-markets
- https://help.kalshi.com/en/articles/13823822-market-rules
- https://help.kalshi.com/en/articles/13823823-rules-summary
- https://developer.weather.com/docs/openapi/historical-conditions-hourly-3-0
- https://developer.weather.com/docs/openapi/time-series-observations-current-hours-past-24-0-0
- https://developer.weather.com/docs/current-historical

## Decision

This source lock strengthens the settlement-target definition but does not establish signal edge or market edge. Keep NO_PROVEN_EDGE. Next decisive work is contract-specific station/time canonicalisation plus immutable point-in-time capture; do not infer undocumented TWC internals.
