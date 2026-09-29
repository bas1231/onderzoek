# Local Bridge Divergence — 2026-09-29

Do not blindly reinstall the old `control/tampermonkey_multichat/` baseline over the active machine.

Before command-bus migration the machine had deliberate local changes that were created during incident repair:

- active Tampermonkey userscript: local v0.5.2 line, not the repository v0.4.7 baseline;
- v0.5.2 uses fail-closed one-send-attempt behavior and removed the post-send `wakeGeneration` abort;
- active `command_router.py` has a local compatibility `RESULT_ACK` intercept and reports `result_ack:true` in health;
- active `bridge_server.py` contains the local `bridge_ping_status_mapping_v1` formatter fix;
- the legacy RESULT_ACK experiment did not solve assistant -> WSL DOM detection and is not part of the primary command-bus architecture.

The command-bus installer intentionally patches the active `bridge_server.py` narrowly/in-place so those unrelated local formatter changes are preserved. It does not overwrite the active userscript or router.

Canonical new-session behavior is defined by:

- `control/bridge_commands/OPERATIONS.md`
- `control/tampermonkey_multichat/PROTOCOL.md`

The GitHub command bus is primary. The legacy userscript/RESULT_ACK paths are compatibility/diagnostic only.
