# Hardened v8 wake runtime integration

Status: provisional Tier-A infrastructure
Task: `TIERA-BRIDGE-COMMAND-BUS-20260929-E001`

## Runtime discovered on 2026-09-29

The active local `~/.local/share/prediction-chat-bridge/bridge_server.py` is not the plain canonical `bridge_server_v2.py`. It is the hardened wrapper line with `server_version = "PredictionChatWake/0.8-hardened"` and:

```python
import bridge_server_v2 as base
```

The wrapper owns compaction, task dedupe, server heartbeat, nightshift userscript serving and health metadata. Queue paths and the base `/next` + `/ack` implementation remain owned by `bridge_server_v2.py`.

The first command-bus installer failed closed because the inflight patcher incorrectly tried to find base-server anchors in the hardened wrapper. No partial patch was accepted and rollback restored the wake runtime/outbox.

## Correct integration boundary

Do **not** replace or flatten the hardened wrapper.

For fail-closed result delivery:

- request target remains the active `bridge_server.py`;
- patcher detects `import bridge_server_v2 as base`;
- actual patch target becomes sibling `bridge_server_v2.py`;
- wrapper remains byte-for-byte untouched by the inflight patch;
- base `/next` atomically moves `OUTBOX -> INFLIGHT` before browser delivery;
- base `/ack` accepts `INFLIGHT` first and moves it to `SENT`;
- no automatic `INFLIGHT -> OUTBOX` retry exists.

This composition preserves existing hardened wrapper behavior while removing the stale-outbox head-of-line blocking failure that was observed on 2026-09-29.

## Deterministic qualification requirements

`control/bridge_commands/selftest.py` must prove both direct-base and hardened-wrapper composition, wrapper non-modification and patch idempotence.

The installer must:

1. back up both active wrapper and base when the wrapper architecture is detected;
2. preserve old outbox evidence in quarantine;
3. patch and compile the base module;
4. restart the existing wake service;
5. require hardened health guardrails (`server_compaction` and `task_dedupe`) to remain true;
6. install the read-only GitHub poller/timer only after those checks pass;
7. restore wrapper, base and outbox on failure.

## Safety

The WSL poller remains GitHub read-only. No live trading, paid actions, wallet actions or autonomous Git pushes are enabled by this integration.

Final status remains `REQUIRES_HIGH_INTELLIGENCE_REVIEW` until an independent Tier-A review is complete.
