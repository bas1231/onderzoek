# A19B validation note

CHECK 3/3 initially failed on 2026-09-21 even though the replay decoder returned top-level `status: PASS`.

Root cause: `ingest_payload()` used decoded station evidence internally to derive PASS, but omitted the `decoded_wrapper` from the persisted result. The validator therefore could not independently verify `matched_station_count`, `matched_stations`, or requested-station coverage.

Fix:
- preserve the full immutable decoder evidence under `result["decode"]`;
- add a unit regression assertion requiring PASS records to retain nested station provenance;
- keep replay ineligible for both adapter-first-seen and queue-insertion latency evidence.

This was a provenance failure, not a decoder or NOAA-data failure. No gate threshold or fail-closed rule was loosened.

Economic conclusion remains `NO_PROVEN_EDGE`.
