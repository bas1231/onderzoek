# REDDIT_IDEA_MINE: Reddit discussion discovery ingress

This is a bounded *discovery-only* adapter with an offline intake path and an
optional fixed-host, read-only Arctic Shift source. It cannot authorize an
experiment, a model review, or a trade. Actual scheduled source polling has
not been activated or proven in the production research runtime.

## Source ingest
Run `python3 control/reddit_idea_mine/ingest.py --input threads.json --output leads.json`.
Input is a list of supplied Reddit discussions. A thread supplies id,
subreddit, URL, title, selftext, created_utc, comments, and source; provenance
must be one of `test_fixture`, `manual_submission`, `authorized_export`,
`licensed_archive`, or the explicitly unverified public source label
`public_archive_unverified`. Only five prediction-market subreddits are ingested.
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

## Arctic Shift bounded HTTPS source (E014/E015)
`control/reddit_idea_mine/arctic_shift_source.py` is repository-owned
standard-library Python only. It can read recent posts and up to 8 sets of
comments through the documented Arctic Shift API, without installing third-party
executables/packages. One source pull makes at most 13 network requests.

Network security invariants:
- **Fixed HTTPS host:** `arctic-shift.photon-reddit.com`; only
  `/api/posts/search` and `/api/comments/search` paths
- TLS verification enabled; redirects and ambient environment proxy use disabled
- No cookies, credentials, shell/subprocess, module downloads or executable content
- 12-second per-call timeout, 2 MB response cap, bounded searches and comments
- Default seven-day search window, adjustable within 30 days; no 30-minute freshness gate
- Bounded comment enrichment rotates between subreddits each hour, keeping criticism and counterarguments representative instead of favoring the first subreddit
- Fail-soft per subreddit with visible errors; malformed JSON is not trusted
- Remote comments/title/body are data only, never privileged model instructions
- The source label is `public_archive_unverified`, not a claim of licensing
- `NO_PROVEN_EDGE`, zero trades, zero experiment authorization

To manually run from an already **authorized network-capable Prediction
runtime**, with an existing controlled inbox directory:

```bash
python3 -m control.reddit_idea_mine.arctic_shift_source --inbox <SAFE_INBOX>
python3 -m control.reddit_idea_mine.source_inbox --inbox <SAFE_INBOX> --root <SAFE_ROOT>
```

Do **not** run the network collector inside the restricted project executor.
Its child guard intentionally blocks external network access. Tests pass
in-memory fixtures to `collect()` and **do not prove remote availability**.
The source is wired **before** canonical `recon.run()` in
`control/hourly/hourly_cycle.py`, using
`PREDICTION_REDDIT_ARCTIC_SHIFT_ENABLED=1` as an explicit opt-in.
The source remains disabled by default, and automatically disabled in the
offline `qualification_local` environment. The existing hourly timer can
be reused; no extra scheduler or automatic activation is installed.

The hourly cycle also records source status and coverage counts in
the checkpointable canonical `knowledge/runs/hourly-*.json` manifest
and under `### Reddit Idea Mine source` in the hourly markdown report.
This uses the existing report and Git-checkpoint allowlist; the detailed
local receipt does not need a new synchronization mechanism.

For each run `hourly_ingress.py` writes a receipt under
`knowledge/runs/reddit_idea_mine` with source status, errors, thread count,
evidence count, and optional post-age metrics. **Speed is not an acceptance\ncriterion**: older useful discussions remain eligible within the bounded\nseven-day default discovery window (up to 30 days when explicitly configured). Untrusted Reddit text carries
`trust_level=untrusted_external_content` and cannot count as a directive.
The normal independent-source, Recon and candidate gates remain required.

`source_canary.py --check` is a one-request read-only source probe: it
reports whether the API returned a usable post, archive retrieval lag if
the archive provides `retrieved_on`, and an error type if unsuccessful.
It never logs post/comment bodies. Offline fixture tests cannot prove live
API availability, uptime, or data completeness. This probe must run in an **already
permitted** network-capable Prediction research runtime; do not work around
the project executor's loopback-only child guard.

**Unmet production gates:**
1. E019 read-only timer/service readiness and E020/E021 code qualifications
   plus E022/E023 source metrics and untrusted-data qualifications
2. Verify the existing research runtime can safely load the canonical source,
   without disturbing the protected production-branch reconciliation
3. Observe a one-shot actual source response with valid API structure and
   useful thread data; post age and ingest lag are only optional telemetry
4. Enable the existing hourly hook only after the preceding gates and confirm
   a real hourly receipt; disable the flag if the provider is persistently unreachable or responses are invalid

No trading, paid API, credentials, bridge edits, autonomous GitHub pushes,
or unrestricted external network access are authorized.

The archive service is public, but the code makes no assertion that Reddit
approved its use. Confirm usage requirements separately from the malware and
host-safety analysis. Never trust Reddit text with command authority.
