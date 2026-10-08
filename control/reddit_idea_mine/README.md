# REDDIT_IDEA_MINE: Reddit discussion discovery ingress

This is a bounded, offline-only *discovery* adapter, not an active Reddit
crawler or a shortcut into experiments.

## Source ingest
Run `python3 control/reddit_idea_mine/ingest.py --input threads.json --output leads.json`.
Input is a list of supplied Reddit discussions. A thread supplies id,
subreddit, URL, title, selftext, created_utc, comments, and source; provenance
must be one of `test_fixture`, `manual_submission`, `authorized_export`,
`licensed_archive`. Only five named prediction-market subreddits are ingested.
Malformed and unrecognized sources are rejected, with counts recorded.

The resulting leads preserve permalinks, timestamps, counterarguments, keyword
matches and stable lead IDs. They carry `DISCOVERY_ONLY_UNVERIFIED` and
`NO_PROVEN_EDGE`, and explicitly deny experiment/model/trading authorization.

## Existing scout / recon governance
- Candidate leads may be reviewed by `recon_scout` and `scout`.
- `control/hourly/recon_candidate_bridge.py` promotes only Recon findings
  with HUNT or PROVE state, passing hunt_gate, *two independent evidence sources*,
  a public trigger and a falsifiable decisive next test.
- An individual Reddit discussion is ONE source, regardless of number of
  comments. Multiple Reddit commenters do not constitute independent sources.
- Promoted findings start `NEEDS_DIRECTOR`; the canonical Sol/Astra gates
  apply to experiments unchanged.
- No direct candidate creation or queue mutation from this adapter.

## Next implementation gate
Functional regression qualification E002, followed by a separate live-source
availability/latency proof and a governed candidate-ingress adapter test. Do
not claim an autonomous live Reddit collector or complete A-to-Z validation
from syntax tests or sample JSON alone.

The project executor prohibits unrestricted outbound network. No credential,
paid API, live trading or Reddit access bypass is authorized by this module.
