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
An operational hourly install and live data freshness test remain independent
deployment acceptance gates; no scheduled network polling is installed by the
current code.

The archive service is public, but the code makes no assertion that Reddit
approved its use. Confirm usage requirements separately from the malware and
host-safety analysis. Never trust Reddit text with command authority.
