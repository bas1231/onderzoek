# Prediction Command Bus — Current State

## Model execution routing target — 2026-10-07

Canonical execution-layer split:

- `SOL_PROPOSAL / SOL_BUILD -> DIRECT_SOL -> exact GPT-5.6 Sol`
- `ASTRA_PREBUILD / ASTRA_POSTBUILD / Astra supervisor review -> CODEX_WORKER -> exact GPT-6 Astra`

Sol must no longer depend on Codex quota. This is currently a **target architecture under implementation**, not yet a proven runtime path. Exact direct-Sol provenance remains mandatory.

The active incomplete R4 Codex attempt is not a scientific rejection. Preserve its governed R4 prompt/binding and Astra R3-P2 feedback when rerunning through DIRECT_SOL, then require a fresh exact GPT-6 Astra POSTBUILD review.

See `control/model_execution/ROUTING.md`.


## Normative A→Z lifecycle target — 2026-10-05

The canonical acceptance criterion for edge-discovery work is now:

`Scout -> selectie -> GPT-5.6 Sol-opzet -> GPT-6 Astra pre-build review -> GPT-5.6 Sol-build -> GPT-6 Astra post-build code-review -> tests en meting -> supervisor -> rapportage`

Mandatory invariant:

`NO_TEST_OR_MEASUREMENT_BEFORE_ASTRA_POSTBUILD_APPROVAL`

Astra must therefore approve both:

1. the version-bound Sol experiment design **before build**; and
2. the exact built code/harness **after build but before substantive tests or measurement**.

At either Astra gate, `NEEDS_REVISION` or rejection returns binding feedback to Sol. Sol revises/rebuilds, produces a newly bound version, and exact GPT-6 Astra reviews again. Tests/backtests/shadow runs/measurements remain blocked until the current built version has valid `ASTRA_POSTBUILD_REVIEW = APPROVE`.

This is a **target architecture and full-chain acceptance requirement**. Do not report a complete A→Z PASS merely because an older runner or fixture follows the former order `build -> tests/measurement -> Astra review`. That former order is non-compliant with the current canonical model-gate policy.

See `methodology/EDGE_DISCOVERY_MODEL_GATES.md` for the normative details.

## Operational update — 2026-10-03

The continuation/result path has advanced beyond the 2026-09-29 baseline below.

### Result receipt route

A GitHub-backed immutable result-receipt mechanism is now operational for browser-delivered Prediction results/continuations. ChatGPT writes a small `PREDICTION_RESULT_RECEIPT_V1` file keyed by the exact wake `event_id` and `source_task_id`; the read-only local command-bus side consumes that receipt and durably moves the matching event to `sent`.

Observed 2026-10-03 evidence includes multiple independent receipt commits and roundtrip verification. In particular:

- `DEV-PRED-CONT-NEXT-97c1e16e78d248be34072b2d` returned `PASS exit=0` for the third independent receipt roundtrip acceptance;
- the acceptance required receipt state `DISPATCHED`, the exact event present in `sent`, and absent from `inflight`;
- a later live continuation receipt `RESULT-RECEIPT-cont-1791058993287-c286ba8f` was followed by durable headless `CONT-DONE-352e53185231a24b9f944580`.

This means the current continuation route no longer depends on Tampermonkey `POST /ack` to establish durable receipt. A diagnostic on the legacy userscript path still observed `runtime_version=0.4.8|ack_count=0`; treat that as a legacy-browser-path defect, not as evidence that the new GitHub result-receipt path is broken.

### Production reconciliation

Production is not yet eligible for an unconditional branch switch/fast-forward.

Read-only inspection proved that the temporary production branch `architecture/sol-builder-astra-reviewer` contains real local architecture commits, including:

- `1170607 build: complete prospective shadow lifecycle`
- `16dcfb2 build: complete autonomous Sol Astra runtime lifecycle`
- `8896d1d fix: accept bounded revision scope`

and changed paths including `control/browser_bridge.py`, new Codex-supervisor build dispatch/planner modules, and related supervisor changes.

Current canonical reconciliation therefore uses fail-closed representation gates. Tasks `DEV-PRED-CONT-NEXT-824b7686cbf56be905e3c2d0` and `DEV-PRED-CONT-NEXT-3c5fd15e7e51abdd487d5847` require both the committed temporary-branch delta and any dirty/untracked production worktree content to be exactly represented in pinned canonical source before any cleanup, switch or fast-forward is authorized.

Do not discard, reset, or overwrite the temporary production branch merely because canonical `main` has advanced. Preserve its ref until the representation gates and final production verification have passed.


Updated: 2026-09-29
Infrastructure track: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`
Session-bootstrap build: `TIERA-SESSION-BOOTSTRAP-20260929-E001`
Intelligence tier: A
Implementation model: GPT-5.6 Sol
Actual reasoning level: `UNAVAILABLE_TO_RUNTIME`
Formal qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Current operational status

The local command bus is installed and operational. The terminal-safe installer preserved the hardened wake wrapper, installed the read-only GitHub poller and activated the systemd timer. The command path is:

`ChatGPT assistant -> private GitHub command file -> read-only WSL poller -> localhost router/receiver -> WSL execution -> wake bridge -> same ChatGPT session route`

The capability-scoped project executor is operational for ordinary Prediction build/test/diagnose/user-level management work inside its documented guardrails.

## Same-chat routing proof observed later on 2026-09-29

This section supersedes the earlier "remaining acceptance gate" wording below for the current session, while preserving the distinction between current-session proof and a separate future brand-new-chat acceptance exercise.

Observed automatically in the current Prediction chat, without a manual bridge/menu ping:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-06b02c18b66873daa2c4548a status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

That task ID became the canonical route for this chat. A fresh command-bus ping was then sent with the explicit route task ID and returned to the same chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=BRIDGE-SESSION-ROUTE-POSTFIX-20260929-E006 status=PASS exit=0 event=1790701888-1436a7343e01`

A follow-up runtime classifier returned:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-ROUTING-RUNTIME-CLASSIFY-20260929-E008 status=PASS exit=0 rcs=1:0 head=1111111111111111111111111111111111111111 event=1790702173-99036e04e37f`

For E008, the all-ones sentinel means the installed router and command-bus poller are the canonical explicit-session implementations rather than the temporary active-page experiment. Together, these observations prove the current chat path:

`this ChatGPT session -> GitHub command bus -> WSL -> wake/result bridge -> this same ChatGPT session`

Operational rule: after an automatic `SESSION-ROUTE-*` PASS appears in a chat, use that task ID explicitly as `route_task_id` for normal commands in that chat. Do not use `route_task_id:null` as the normal multi-session routing method.

### Active-page experiment retired

A temporary focused-page/active-tab routing experiment was tested on 2026-09-29. It was abandoned as the normal routing design because command-bus pickup can occur materially later than command creation, while browser focus can change in the meantime. That creates an avoidable timing race. The canonical design remains automatic per-chat route bootstrap followed by immutable explicit `route_task_id` on each normal command.

`DEV-PRED-ROUTING-STABILIZE-20260929-E005` returned FAIL after its restoration attempt, but later evidence showed the desired canonical runtime was already installed. E008 classified the runtime as canonical, and the independent E006 bridge ping returned PASS through the current session route. Treat E005 as a failed maintenance/verification task, not evidence that the canonical bridge path is broken.

## Transactional auto-continuation status — 2026-10-02

The remaining automatic next-turn problem has been narrowed and implemented repo-side without repairing or depending on Tampermonkey.

Current source on `main` includes:

- deterministic continuation identity derived from the full source task ID;
- explicit command-bus lineage fields `auto_continue` and `parent_continuation_id`;
- durable states separating `CONTINUE_QUEUED` from browser-ACKed `CONTINUE_SENT`;
- downstream success based only on deterministic command-bus outcomes (`NEXT`, `DONE`, `BLOCKED`), never on a send click or browser ACK;
- bounded retry attempts with unique delivery IDs but stable logical continuation/outcome IDs;
- explicit wake ACK hook with compatibility for the installed inflight-patched runtime;
- Chrome extension wake consumer v1.0.0 using canonical `/next` + `/ack`, stable chat identity, and exact observed user-turn confirmation before ACK;
- no dependency on Tampermonkey for the new wake consumer;
- continuation-only recovery of stale ambiguous `inflight` deliveries: stale `control_continuation_v2` events with exact matching continuation identity are moved to an evidence-preserving `continuation_abandoned` directory before a fresh delivery attempt is created. Ordinary result events remain fail-closed and are never automatically replayed.

Source merge for stale-inflight recovery:

`59b4feb048a9b0d1a3ce419e5018b0b9287ce93c`

Headless verification/install task dispatched:

`DEV-PRED-CONT-INFLIGHT-RECOVERY-INSTALL-20261002-E004`

E004 is designed to run continuation regressions, compile checks, install the current command-bus/wake overlay/continuation manager, stage Chrome extension v1.0.0, restart only Prediction user services, and execute an installed-runtime canary for stale-inflight recovery.

**Do not claim E004 runtime success from Git history alone.** Because this chat currently has no proven browser wake route, headless dispatch does not return its local executor result here. Runtime acceptance still requires observed executor `PASS exit=0` plus the final product-level no-human-input `A -> ChatGPT turn -> B -> DONE` canary.

Tampermonkey repair is explicitly out of scope for this continuation path.

## Proven command-bus baseline

Successful end-to-end evidence on 2026-09-29:

- `BRIDGE-BUS-AUTO-20260929-E001` -> PASS, exit 0
- `TM-PING-1790690332005` -> PASS, exit 0, returned to the intended chat
- `BRIDGE-COMMAND-BUS-CURRENT-ROUTE-E008` -> PASS, exit 0, returned to that same chat through an explicit session route
- `DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010` -> PASS, exit 0, installed and runtime-verified automatic session bootstrap
- `DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013` -> PASS, exit 0, installed and runtime-verified nested-status-safe result compaction
- `SESSION-ROUTE-06b02c18b66873daa2c4548a` -> PASS, exit 0, automatic route announcement observed in the current chat
- `BRIDGE-SESSION-ROUTE-POSTFIX-20260929-E006` -> PASS, exit 0, fresh explicit-route command returned to the current chat
- `DEV-PRED-ROUTING-RUNTIME-CLASSIFY-20260929-E008` -> PASS, exit 0, canonical router/poller runtime confirmed

This proves the primary GitHub command-bus path once a valid same-chat route exists, plus the installed automatic-bootstrap runtime and corrected DEV result-status compactor.

The main legacy result-path failure found earlier was head-of-line blocking. The installed result queue uses fail-closed `outbox -> inflight -> sent` semantics; ambiguous `inflight` delivery is not silently treated as sent or automatically replayed.

## Multi-session routing incident

A later test exposed a separate addressing problem: a command could execute correctly while its result was routed to an older/global pinned ChatGPT route instead of the session that issued it.

The explicit per-command `route_task_id` rule fixed normal multi-session command delivery once the current chat had a known route. However, the original new-chat bootstrap procedure still depended on a legacy visible DOM marker or manual menu ping. That was an incomplete solution because the legacy assistant-DOM command scanner had already proven unreliable.

## Automatic new-session bootstrap — installed

Task:

`DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010`

Observed result in the controlling chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-SESSION-BOOTSTRAP-INSTALL-20260929-E010 status=PASS exit=0 rcs=1:0 head=529896aaae12b3be4e1f13ec1ae177a781410605 event=1790693622-48084ad6d046`

E010 performed the following before returning PASS:

1. ran the deterministic session-bootstrap regression suite;
2. ran compile checks for the new wrapper and hardened bridge module;
3. installed the hardened bridge module to the allowlisted Prediction runtime;
4. installed `bridge_server_session_bootstrap.py` as the active `bridge_server.py` runtime;
5. restarted `prediction-chat-wake.service`;
6. required the service to be active;
7. imported the installed runtime and required `Handler.server_version == "PredictionChatWake/0.9-session-bootstrap"`;
8. ran an installed-runtime canary that created a `SESSION-ROUTE-*` route and corresponding PASS announcement.

Canonical implementation:

`control/tampermonkey_multichat/bridge_server_session_bootstrap.py`

The wrapper uses the already-existing wake `/next` poll. Current Prediction browser tabs already send a stable `chat_id` plus `consumer_id` when polling for results. For a chat without a previously proven routed result, the wake server now creates a deterministic chat-scoped route and an idempotent announcement:

`NIGHTSHIFT_WSL_RESULT_V1 task=SESSION-ROUTE-... status=PASS exit=0 kind=SESSION_ROUTE_BOOTSTRAP`

After that result is ACKed in the same chat, the `SESSION-ROUTE-*` task ID is the canonical `route_task_id` for GitHub command-bus work from that session.

The normal new-session procedure therefore no longer requires the assistant to emit a visible `[[PREDICTION_CMD:...]]` marker. Legacy/menu PING remains diagnostic fallback only.

## Result compaction incident — fixed and installed

A follow-up diagnostic exposed a browser-facing status compaction bug. Task `DEV-PRED-ROUTE-BOOTSTRAP-DIAG-20260929-E011` returned the contradictory summary:

`status=FAIL exit=0 rcs=1:2,1:0 error=TaskError`

E011 intentionally printed the stored receipt of the older failed E009 task. The outer DEV runner then completed its own command with RC 0 and printed its final `DEV_TASK_STATUS=PASS`. The old hardened compactor selected the first embedded `DEV_TASK_STATUS`, first `ERROR_CLASS`, and historical `COMMAND_n_RC` markers from raw output, so an embedded historical failure could incorrectly flip the browser summary of a successful diagnostic to FAIL.

The fix was installed by:

`DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013`

Observed result in the controlling chat:

`NIGHTSHIFT_WSL_RESULT_V1 task=DEV-PRED-STATUS-COMPACTION-FIX-20260929-E013 status=PASS exit=0 rcs=1:0 head=a43ad4a2a3014e36ec1932b4b4b31b7fd269f140 event=1790695022-7d3aaf3f690e`

E013 ran the nested-status regression test and compile checks, installed `bridge_server_status_compaction.py` as the active wake runtime, restarted and required `prediction-chat-wake.service` active, and executed a runtime assertion requiring the outer PASS to remain authoritative even when an embedded older receipt contains FAIL/TaskError/RC=2.

Canonical implementation:

- `control/tampermonkey_multichat/bridge_server_status_compaction.py`
- `control/tampermonkey_multichat/test_status_compaction_nested.py`

This incident was a result-summary/reporting defect; it did not invalidate E010 or prove a command-bus/session-bootstrap execution failure.

## Acceptance status for automatic bootstrap

E010 proves implementation, deterministic behaviour, installation, service restart, service liveness and installed-runtime canary. E013 proves the corrected result-status compactor is installed and runtime-verified.

Automatic bootstrap has now also been directly observed in the current Prediction chat as `SESSION-ROUTE-06b02c18b66873daa2c4548a -> PASS`, followed by a fresh explicit-route command `BRIDGE-SESSION-ROUTE-POSTFIX-20260929-E006 -> PASS` returning to that same chat.

This closes the operational acceptance gate for the current session. A separately opened genuinely brand-new Prediction chat can still be used as an additional product-level regression test for zero-history startup, but it is no longer required to establish that the present session's same-chat command path works.

## Project executor operational proof

Successful evidence:

- `DEV-PRED-PROJECT-EXEC-INSTALL-E002` — compile + deterministic unittest suite PASS;
- `DEV-PRED-PROJECT-EXEC-CANARY-E001` — isolated worktree, repository-owned Python write/execute and local Git inspection PASS;
- `DEV-PRED-PROJECT-EXEC-OPS-E003` — Python execution, isolated local Git commit, bounded runtime install, `prediction-*` user-service inspection and Prediction journal-read path PASS.

The executor uses a repository-local Git identity in its isolated worktrees and does not mutate the user's global Git identity.

## Canonical routing rule

See `control/bridge_commands/SESSION_ROUTING.md`.

In summary:

- each active Prediction chat uses its own explicit same-chat route;
- brand-new chats are expected to receive an automatic `SESSION-ROUTE-*` bootstrap from the wake server;
- after that PASS, use the route task explicitly on every normal command from that chat;
- do not normally use `route_task_id:null` when multiple sessions may exist;
- `DISPATCHED` is not successful same-chat delivery;
- command task IDs are immutable and at-most-once; never reuse a claimed command to repair delivery.

## Canonical implementation/docs

- `00_CHATGPT_START_HERE.md` — mandatory first read.
- `control/bridge_commands/SESSION_ROUTING.md` — per-session routing and automatic bootstrap.
- `control/bridge_commands/OPERATIONS.md` — command-bus operations.
- `control/NEW_SESSION_LOCAL_EXECUTION.md` — project execution flow.
- `control/PROJECT_EXECUTOR.md` — executor capabilities/guardrails.
- `control/tampermonkey_multichat/PROTOCOL.md` — bridge protocol.
- `control/tampermonkey_multichat/bridge_server_session_bootstrap.py` — automatic bootstrap wrapper.
- `control/tampermonkey_multichat/test_session_route_bootstrap.py` — regression suite.
- `control/tampermonkey_multichat/bridge_server_status_compaction.py` — installed nested-receipt-safe result compactor.
- `control/tampermonkey_multichat/test_status_compaction_nested.py` — regression suite for result status parsing.
- `control/bridge_commands/COMMAND_SCHEMA_V1.json` — immutable command schema.
- `control/bridge_commands/command_bus_poller.py` — read-only GitHub poller with durable command claims.

## Guardrails

Unchanged:

- WSL side is GitHub read-only: no autonomous push/publication;
- no live trading;
- no paid action without the separately required exact approval;
- no wallet/crypto action;
- no credential reads/writes;
- no unrestricted root/sudo;
- no unrestricted external networking from project code;
- command claims are durable before localhost dispatch;
- ambiguous command dispatches are never automatically retried;
- ambiguous result delivery remains fail-closed;
- production working tree is not the command-bus fetch target.

## Qualification gate

The command bus, explicit session routing, project executor, automatic session-bootstrap runtime and corrected result compactor are operationally implemented and have passed their documented local/runtime tests. The current session also has direct automatic-bootstrap and same-chat round-trip evidence. Formal independent Tier-A qualification remains `REQUIRES_HIGH_INTELLIGENCE_REVIEW`. Operational evidence must not be used to relax trading, cost, wallet, credential, provenance or autonomy guardrails.
