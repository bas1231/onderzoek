# Plus-native Research OS canary

Status: **DESIGN ONLY — DO NOT ACTIVATE YET**

Date: 2026-09-21

## Product constraints used by this design

OpenAI currently documents that ChatGPT Plus supports up to five active Scheduled Tasks and that Scheduled Tasks can run at most once per hour. Tasks can use connected apps when available and within configured permissions. Plus usage limits still apply to task runs.

The repository's current AI transport is explicitly single-turn and does not use the OpenAI API. The purpose of this canary is to determine whether native ChatGPT Plus task/app capabilities can provide useful independent work lanes without introducing paid API infrastructure.

## Five-slot hypothesis

The five available task slots should map to work lanes, not one task per old agent role.

1. `PRIMARY_SCOUT` — high-quality primary/academic/code discovery.
2. `RECON_SCOUT` — orthogonal weak-signal/offensive economic reconnaissance.
3. `SPECIALIST_DISPATCH` — dynamically executes the highest-value Market Research, Mechanics or Algebra task.
4. `RED_TEAM_REPRO` — Red Team by default; temporary blind reproduction only when a serious survivor requires it.
5. `DIRECTOR` — reconciles artifacts, applies gates, schedules next decisive questions and publishes the consolidated report.

This mapping preserves six responsibility domains even though only five persistent task slots exist: Market Research, Mechanics and Algebra share one dynamic specialist slot rather than each consuming a permanent scheduled-task slot.

## Proposed staggered hourly shape

This is a canary hypothesis, not a promise about exact runtime/concurrency:

- minute 00: Primary Scout
- minute 00: Recon Scout
- minute 15: Specialist Dispatch
- minute 35: Red Team/Reproducer
- minute 50: Director

The stagger is intended to create dependency order within an hour while allowing the two discovery lanes to operate independently.

If the product does not guarantee the assumed sequencing or app behavior, the design must adapt to observed task semantics rather than inventing completion.

## Canary questions that must be answered before migration

### C1 — GitHub access in scheduled context

Can a task read the connected GitHub repository at run time?

PASS only if the task can fetch a known non-secret canary file and report the exact branch/commit it observed.

### C2 — GitHub write behavior

Can the scheduled task create a non-secret artifact on a dedicated canary branch using the connected app permissions?

PASS only if:
- no human credential is printed or requested;
- the write lands only on the dedicated canary branch;
- the artifact contains an idempotency key and source commit;
- rerunning the same logical task does not create duplicate evidence.

If write is unavailable, do not treat this as a product failure. Keep Git write through the existing bridge/control plane and use the task only to produce a chat result for ingestion.

### C3 — Context isolation

Do Scout A and Scout B receive sufficiently independent context to avoid correlated search?

PASS requires different source/query-family instructions and measured overlap. Identical or near-identical outputs count against the design.

### C4 — Result persistence

Can Director reliably see the artifacts/results from earlier lanes without relying on transient conversational memory?

PASS requires canonical artifact references. If native task chats are isolated, use Git/control-plane artifacts rather than assuming shared memory.

### C5 — Scheduling semantics

Do the staggered task times provide reliable enough ordering for Specialist and Director to consume completed upstream outputs?

PASS requires observed ordering across multiple runs. Missing or late upstream tasks must produce an explicit `UPSTREAM_NOT_READY`, not stale fallback.

### C6 — Duplicate delivery/idempotency

Can retries or duplicate notifications cause a claim/result to be ingested twice?

PASS requires stable `(task_id, logical_run_id, source_commit)` idempotency.

### C7 — Usage-limit degradation

What happens when Plus task/model allowance is constrained?

PASS requires the queue to remain durable and no fabricated substitute result. Capacity loss should degrade throughput, not scientific standards.

### C8 — No hidden cost path

Confirm no OpenAI API key, paid API, cloud worker or paid external source is introduced.

PASS is mandatory.

## Fallback hierarchy

1. Native Plus task + connected GitHub app if canary proves adequate behavior.
2. Native Plus task produces result; existing local bridge writes validated result to Git.
3. Existing single-turn hourly factory remains canonical baseline.

Never silently jump from a failed free path to a paid API path.

## Model allocation principle

Use the strongest Plus-available reasoning setting for tasks where deep synthesis/falsification materially matters, and cheaper/faster product modes where deterministic or shallow triage is sufficient, subject to actual product availability and plan limits.

Do not hard-code model names into scientific semantics. The worker contract and evidence requirements must survive model changes.

Suggested capability allocation:
- Director: high reasoning.
- Red Team/Reproducer: high reasoning.
- Algebra: high reasoning when invoked.
- Primary/Recon discovery: enough reasoning for source discrimination, with local deterministic dedupe before model context.
- mechanical parsing/hash/change detection: local code, not model tokens.

## Activation rule

This canary may be implemented only after the pre-build architecture suite is accepted. Passing the canary authorizes a shadow transport experiment only; it does not authorize replacing the current factory, live trading, paid actions or wallet actions.

Economic status remains `NO_PROVEN_EDGE`.
