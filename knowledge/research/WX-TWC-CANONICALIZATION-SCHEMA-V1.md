# WX-TWC-CANONICALIZATION-SCHEMA-V1

Status: RESEARCH_SPEC
Economic conclusion: NO_PROVEN_EDGE
Safety: no live trading, no paid actions, no wallet actions

## Purpose
Define the minimum point-in-time fields and fail-closed rules required before any Weather Runner signal model may treat a Kalshi hourly temperature contract as a valid TWC target.

## Required canonical record

For each market-time target, persist:

- venue
- series_ticker
- event_ticker
- market_ticker
- contract_title
- rule_text_sha256
- rule_retrieved_at
- rules_version_or_observation_id
- official_settlement_source
- station_identifier_if_explicit
- station_coordinates_if_explicit
- market_timezone
- named_settlement_local_time
- named_settlement_utc_time
- comparator
- strike
- market_close_time
- source_url_or_api_endpoint
- mapping_status
- ambiguity_reason

## Mapping status

Only one of:

- CANONICAL: station/location, exact time, timezone and TWC target are all explicit and internally consistent in point-in-time evidence.
- PARTIAL: some required mapping fields are present but at least one required field is not explicit.
- AMBIGUOUS: multiple plausible mappings or conflicting rule/source evidence exist.
- INVALID: rule/source evidence shows the market is not an hourly TWC target.

Only CANONICAL records are eligible for downstream signal-edge testing.

## Fail-closed rules

1. Never infer a station from city name alone when rules do not explicitly establish the mapping.
2. Never infer TWC as settlement source from series family alone when contemporaneous market/rule evidence says otherwise or is absent.
3. Never convert a local settlement time to UTC without an explicit timezone and date-aware conversion.
4. Preserve the exact rule text or raw API response hash used for the mapping.
5. Preliminary TWC values are not interchangeable with final settlement values.
6. Public TWC developer API values must not be assumed identical to Kalshi settlement feed values without direct contract-specific evidence.
7. Any rule change, station change, timezone conflict or source conflict invalidates reuse of an older canonical mapping until re-canonicalized.
8. Market buckets sharing one settlement target are grouped under the same canonical target key and are not treated as independent events.

## Canonical target key

Preferred conceptual key:

`venue | official_settlement_source | station_or_coordinates | named_settlement_utc_time | rules_version`

If station/coordinates or rules version is unavailable, mapping_status cannot be CANONICAL.

## Required downstream join discipline

Meteorological observations, TWC observations, model outputs and market L2 must join through the canonical target key plus their own observation/retrieval timestamps. No later or revised data may be backfilled as if it were available before market close.

## Acceptance gate for the next phase

Before Weather Runner Phase 0A uses a contract in model evaluation:

- contract mapping is CANONICAL;
- rule/source evidence predates or is contemporaneous with the prediction decision;
- exact settlement time is normalized without timezone ambiguity;
- target is explicitly the final TWC settlement value;
- all non-canonical cases are excluded and counted.

## Negative-evidence handling

Track and report excluded markets by reason. A high exclusion rate is itself evidence that broad automated canonicalization is not yet trustworthy and should block model promotion rather than be silently repaired with heuristics.

## Current decision

This schema does not establish signal edge or market edge. It only defines the semantic gate required to prevent target leakage and wrong-settlement modelling. Keep NO_PROVEN_EDGE until later out-of-sample signal and executable market tests pass.