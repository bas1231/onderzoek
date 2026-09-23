#!/usr/bin/env python3
"""Patch the locally tested Prediction Chat Wake Bridge v0.3.5 to v0.3.6.

This deliberately does NOT reconstruct the userscript from GitHub main.  The live
browser copy may be newer than main.  It patches only the known v0.3.5 scanner
surface and aborts closed if that surface is not present exactly once.

v0.3.6 goals:
- inspect only the newest explicit assistant turn (never generic article history);
- ignore code/pre/blockquote examples;
- require a standalone command-marker line;
- tolerate ChatGPT rendering separator colons as `\:`;
- never scan while ChatGPT is still generating;
- remember HTTP 409 route conflicts so they are not retried forever;
- deduplicate task IDs globally, because the protocol requires unique task IDs.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v036")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")

if "// @version      0.3.6" in src and "const SCRIPT_VERSION = '0.3.6';" in src:
    print("OK: userscript is al v0.3.6; niets gewijzigd.")
    raise SystemExit(0)

if "// @version      0.3.5" not in src or "const SCRIPT_VERSION = '0.3.5';" not in src:
    versions = "\n".join(
        line for line in src.splitlines()
        if "@version" in line or "SCRIPT_VERSION" in line
    )
    die("verwacht exact lokale v0.3.5 als basis. Gevonden:\n" + versions)

# Refuse to patch the old 0.3.3 scanner or another unknown local variant.
if "function commandScanRoots()" not in src or "function visibleCommandMarkers()" not in src:
    die("v0.3.5 commandScanRoots/visibleCommandMarkers niet gevonden")

shutil.copy2(PATH, BACKUP)

scanner_pattern = re.compile(
    r"  function commandScanRoots\(\) \{.*?\n  async function sendCommand\(marker, identity\) \{",
    re.S,
)

scanner_replacement = r'''  function commandScanRoots() {
    // Fail closed: only explicit assistant-role containers are command sources.
    // Never fall back to generic conversation/article wrappers because those can
    // include user text or historical examples.
    const selectors = [
      '[data-message-author-role="assistant"]',
      'article[data-turn="assistant"]',
      'article[data-turn-id][data-turn="assistant"]'
    ];

    for (const selector of selectors) {
      let nodes = [];
      try {
        nodes = Array.from(document.querySelectorAll(selector))
          .filter(node => node && node.isConnected && !node.closest?.('form'));
      } catch (_) {}
      if (nodes.length) return [nodes[nodes.length - 1]];
    }
    return [];
  }

  function commandTextWithoutExamples(root) {
    try {
      const clean = root.cloneNode(true);
      clean.querySelectorAll?.('pre, code, blockquote').forEach(node => node.remove());
      return String(clean.innerText || clean.textContent || '');
    } catch (_) {
      return '';
    }
  }

  function visibleCommandMarkers() {
    const out = [];
    const seen = new Set();
    const exact = /^\[\[PREDICTION_CMD:([A-Z][A-Z0-9_]{1,79}):([A-Za-z0-9._:-]{1,160})\]\]$/;

    // commandScanRoots intentionally returns only the newest explicit assistant turn.
    for (const root of commandScanRoots()) {
      const text = commandTextWithoutExamples(root);
      if (!text.includes('PREDICTION_CMD')) continue;

      for (const rawLine of text.split(/\r?\n/)) {
        // ChatGPT's renderer can expose escaped colons as "\\:" in visible text.
        // Normalize only inside a standalone candidate line, then validate strictly.
        const line = String(rawLine || '').trim().replace(/\\:/g, ':');
        if (!line.startsWith('[[PREDICTION_CMD')) continue;

        const match = line.match(exact);
        if (!match) continue;

        const markerKey = `${match[1]}:${match[2]}`;
        if (seen.has(markerKey)) continue;
        seen.add(markerKey);
        out.push({ action: match[1], task_id: match[2], markerKey });
      }
    }
    return out;
  }

  async function sendCommand(marker, identity) {'''

src, scanner_count = scanner_pattern.subn(scanner_replacement, src, count=1)
if scanner_count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"scannerblok niet eenduidig gevonden (matches={scanner_count}); backup hersteld")

old_409 = "if (response.status === 409) { status(`route conflict ${marker.task_id}`, true); return false; }"
new_409 = "if (response.status === 409) { status(`route conflict genegeerd ${marker.task_id}`, true); return 'route_conflict'; }"
if old_409 not in src:
    shutil.copy2(BACKUP, PATH)
    die("HTTP-409 patchpunt niet gevonden; backup hersteld")
src = src.replace(old_409, new_409, 1)

old_loop = '''        const dedupeKey = `${identity.chatId}|${marker.markerKey}`;
        if (remembered(KEY_COMMAND_IDS, dedupeKey)) continue;
        const ok = await sendCommand(marker, identity);
        if (ok) {
          remember(KEY_COMMAND_IDS, dedupeKey);
          status(`command ${marker.action}: ${marker.task_id}`);
        }'''

new_loop = '''        // Task IDs are globally unique by protocol.  Global dedupe prevents a
        // copied historical marker from being replayed in another chat.
        const dedupeKey = `global|${marker.markerKey}`;
        if (remembered(KEY_COMMAND_IDS, dedupeKey)) continue;

        const result = await sendCommand(marker, identity);
        if (result === true) {
          remember(KEY_COMMAND_IDS, dedupeKey);
          status(`command ${marker.action}: ${marker.task_id}`);
        } else if (result === 'route_conflict') {
          // A conflicting task already belongs elsewhere.  Remember it so the
          // scanner does not hammer the router every polling cycle.
          remember(KEY_COMMAND_IDS, dedupeKey);
        }'''

if old_loop not in src:
    shutil.copy2(BACKUP, PATH)
    die("scanCommands-loop patchpunt niet gevonden; backup hersteld")
src = src.replace(old_loop, new_loop, 1)

# Ensure scans are suppressed during streaming even if the local v0.3.5 variant
# did not already include that guard.
old_guard = "if (scanBusy || !enabled() || !token()) return;"
new_guard = "if (scanBusy || chatIsBusy() || !enabled() || !token()) return;"
if old_guard in src:
    src = src.replace(old_guard, new_guard, 1)
elif new_guard not in src:
    shutil.copy2(BACKUP, PATH)
    die("scanCommands busy-guard niet herkenbaar; backup hersteld")

src = src.replace("// @version      0.3.5", "// @version      0.3.6", 1)
src = src.replace("const SCRIPT_VERSION = '0.3.5';", "const SCRIPT_VERSION = '0.3.6';", 1)
src = src.replace("WSL bridge v3.5:", "WSL bridge v3.6:")

PATH.write_text(src, encoding="utf-8")

print(f"OK: v0.3.6 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Wijzigingen: newest-assistant-only, voorbeelden genegeerd, \\: tolerant, 409 dedupe.")
