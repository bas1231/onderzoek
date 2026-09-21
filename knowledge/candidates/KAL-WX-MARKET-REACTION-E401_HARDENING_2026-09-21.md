# KAL-WX-MARKET-REACTION-E401 — hardening status — 2026-09-21

Status: **SOFTWARE HARDENED / INDEPENDENT STRIX VALIDATION PENDING / PROSPECTIVE EVIDENCE PENDING / NO_PROVEN_EDGE**

## Purpose

E401 measures how quickly executable KXTEMP market state changes after the preregistered E390 `first_decision_eligible` KWI signal. It is an evidence/falsification gate only. It does not place orders and does not establish profitability.

The 2026-09-21 external corroboration note materially reduced novelty of broad early-KWI reconstruction. Therefore the decisive question remains synchronized market reaction and executable depth, not further weather-model optimization.

## Canonical hardening added

### 1. WebSocket evidence integrity

Commit `320f0b988601392add90f908715be7f069671b1d` hardens the authenticated read-only WS recorder:

- every successfully decoded WS frame records a transport-coverage marker, including during busy sockets where idle heartbeats would never fire;
- malformed replacement snapshots invalidate/reset the reconstructed book;
- sequence/delta reconstruction errors invalidate/reset the reconstructed book;
- reconnect intervals are explicitly recorded as capture gaps;
- reconnects use bounded backoff;
- credential material remains excluded from logs;
- no order/write/wallet endpoint is added.

Targeted offline hardening tests: **5/5 PASS**.

### 2. Primary-sample independence

Commit `279b4f821f7a2f55e2d108cb53b80cb0ce9f7c99` fixes a protocol-risk in the offline analyzer.

`extract_kwi_events()` legitimately emits both the first qualifying signal and later same-target revisions. The analyzer now separates them explicitly:

- `first_decision_eligible` -> independent primary E401 sample;
- `revision` -> diagnostic only, never an independent primary sample;
- unknown event kinds -> fail closed outside the primary sample.

`events_total` and `primary_events_total` now count primary events only. Revisions are retained in `revision_results` and reported separately.

Targeted offline independence tests: **2/2 PASS**.

This prevents the preregistered `>=30` event threshold from being inflated by multiple revisions of one city x target KWI minute.

### 3. Evidence-threshold summary

Commit `583cb3126ade5c64edb5746c540ea92aee03cbf6` adds a fail-closed cross-report E401 summarizer.

It enforces:

- only schema `KAL_WX_MARKET_REACTION_E401_V2` counts;
- legacy V1 reports are rejected because they may mix revisions into the primary sample;
- independence key = `city x target KWI minute`;
- identical duplicate events are deduplicated;
- conflicting duplicate events fail dataset integrity;
- malformed/unknown primary results fail dataset integrity;
- `UNPROVEN_REACTION` counts against synchronized-capture coverage;
- the preregistered thresholds remain `>=30` unique primary events, `>=2` evaluable cities, and `>=95%` valid synchronized capture coverage;
- meeting those thresholds only permits consideration of E402; it does **not** imply market edge or profitability.

Targeted offline summary tests: **6/6 PASS**.

## Canonical validation bundle

`control/weather/validate_market_reaction_e401.py` now compiles and runs the E401 core, transport-hardening, primary-sample independence, and evidence-summary tests as one no-network validation bundle.

Queued local validation tasks include:

- `EDGE-HUNTER-KWI-MARKET-REACTION-VALIDATE-E401`
- `EDGE-HUNTER-KWI-MARKET-REACTION-PREFLIGHT-E401A1`
- `EDGE-HUNTER-KWI-MARKET-REACTION-HARDEN-E401R1`
- `EDGE-HUNTER-KWI-MARKET-REACTION-VALIDATE-E401R2`
- `EDGE-HUNTER-KWI-MARKET-REACTION-VALIDATE-E401R3`

At the time of this note, no corresponding independent Strix `RESULT.json` has been observed in canonical Git. Therefore independent local validation is still **PENDING**, regardless of the offline build tests above.

## Prospect capture remains blocked from automatic activation

No live/prospective WS capture has been activated by these changes.

Before prospect capture becomes canonical evidence:

1. the local E401 validation bundle must return PASS;
2. the read-only credential/dependency preflight must confirm availability without printing secrets;
3. capture must remain authenticated read-only, with no orders, wallet actions, paid data or OpenAI API;
4. synchronized KWI + KXTEMP evidence must accumulate prospectively under the frozen E401 definitions;
5. E402 must not start until the E401 minimum-evidence gate is met.

## Current economic conclusion

- signal phenomenon: research-positive at E390 / externally corroborated broadly;
- market reaction timing: **UNPROVEN prospectively**;
- market edge: **UNPROVEN**;
- execution edge: **UNPROVEN**;
- profitability: **UNPROVEN**.

**NO_PROVEN_EDGE**.
