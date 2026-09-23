#!/usr/bin/env python3
"""Upgrade the local Prediction Chat Wake Bridge scanner to v0.4.0.

This patch deliberately keeps the proven localhost routing/wake path intact and
replaces only the fragile ChatGPT DOM command-detection layer.

v0.4.0 design:
- no full-conversation MutationObserver;
- inspect only the newest explicit assistant turn;
- wait until generation is no longer busy and the turn is stable;
- treat ChatGPT's copy-action as an extra completion signal when available;
- accept a standalone PREDICTION_CMD line whether ChatGPT exposes ':' or '\\:';
- allow the marker to be rendered as code (innerText is the source of truth);
- refuse ambiguous turns containing multiple different command markers;
- global task/action dedupe;
- HTTP 409 route conflicts are remembered and never hammered repeatedly.

The patch accepts the known 0.3.x local variants and aborts closed if the
expected scanner surfaces cannot be found. A backup is created before writing.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v040")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")

if "// @version      0.4.0" in src and "const SCRIPT_VERSION = '0.4.0';" in src:
    print("OK: userscript is al v0.4.0; niets gewijzigd.")
    raise SystemExit(0)

version_match = re.search(r"^// @version\s+([^\s]+)", src, re.M)
script_match = re.search(r"const SCRIPT_VERSION = '([^']+)';", src)
if not version_match or not script_match:
    die("versieregels niet gevonden")

old_version = version_match.group(1)
if not old_version.startswith("0.3."):
    die(f"verwacht een bekende 0.3.x-basis, gevonden {old_version}")

if "async function sendCommand(marker, identity)" not in src:
    die("sendCommand niet gevonden")
if "async function scanCommands()" not in src:
    die("scanCommands niet gevonden")

# Need either the original 0.3.3 scanner or the 0.3.5/0.3.6 scanner.
scanner_start = None
for candidate in ("function commandScanRoots()", "function assistantRoots()"):
    pos = src.find(candidate)
    if pos >= 0 and (scanner_start is None or pos < scanner_start):
        scanner_start = pos
if scanner_start is None:
    die("bekende command-scanner niet gevonden")

shutil.copy2(PATH, BACKUP)

scanner_pattern = re.compile(
    r"  function (?:commandScanRoots|assistantRoots)\(\) \{.*?\n  async function sendCommand\(marker, identity\) \{",
    re.S,
)

scanner_replacement = r'''  // ---- v0.4 command response-cycle scanner -----------------------------
  let commandTurnKey = '';
  let commandTurnFingerprint = '';
  let commandTurnStableSince = 0;

  function resetCommandTurnTracker() {
    commandTurnKey = '';
    commandTurnFingerprint = '';
    commandTurnStableSince = 0;
  }

  function newestAssistantTurn() {
    // Prefer the stable author-role attribute used by ChatGPT message nodes.
    // Fallbacks remain explicit assistant-only selectors; never generic articles.
    const selectors = [
      '[data-message-author-role="assistant"]',
      'article[data-turn="assistant"]',
      'article[data-turn-id][data-turn="assistant"]'
    ];

    for (const selector of selectors) {
      try {
        const nodes = Array.from(document.querySelectorAll(selector))
          .filter(node => node && node.isConnected && !node.closest?.('form'));
        if (!nodes.length) continue;

        const root = nodes[nodes.length - 1];
        const container = root.closest?.(
          '[data-turn-id], [data-testid^="conversation-turn-"], article'
        ) || root;
        const explicitId = String(
          container.getAttribute?.('data-turn-id') ||
          container.getAttribute?.('data-testid') ||
          root.getAttribute?.('data-message-id') ||
          ''
        );
        const key = explicitId
          ? `assistant:${explicitId}`
          : `assistant-index:${nodes.length - 1}`;

        return { root, container, key };
      } catch (_) {}
    }
    return null;
  }

  function assistantTurnText(turn) {
    if (!turn?.root) return '';
    try {
      // Deliberately do NOT remove code/pre elements. ChatGPT often renders an
      // exact machine marker as code. innerText is what the browser actually sees.
      return String(turn.root.innerText || turn.root.textContent || '');
    } catch (_) {
      return '';
    }
  }

  function assistantTurnHasCopyAction(turn) {
    const scope = turn?.container || turn?.root;
    if (!scope) return false;
    try {
      return !!scope.querySelector?.(
        '[data-testid="copy-turn-action-button"], button[aria-label*="Copy" i], button[aria-label*="Kop" i]'
      );
    } catch (_) {
      return false;
    }
  }

  function assistantTurnFingerprint(turn, text) {
    let childCount = 0;
    try { childCount = Number(turn?.root?.childElementCount || 0); } catch (_) {}
    const tail = String(text || '').slice(-240);
    return stableHash(`${String(text || '').length}|${childCount}|${tail}`);
  }

  function standaloneCommandFromText(text) {
    const exact = /^\[\[PREDICTION_CMD:([A-Z][A-Z0-9_]{1,79}):([A-Za-z0-9._:-]{1,160})\]\]$/;
    const found = new Map();

    for (const rawLine of String(text || '').split(/\r?\n/)) {
      // Markdown renderers may preserve a backslash that escaped a colon in the
      // source. Normalize that one presentation difference, then validate hard.
      const line = String(rawLine || '')
        .replace(/[\u200B-\u200D\uFEFF]/g, '')
        .trim()
        .replace(/\\:/g, ':');

      if (!line.startsWith('[[PREDICTION_CMD')) continue;
      const match = line.match(exact);
      if (!match) continue;

      const markerKey = `${match[1]}:${match[2]}`;
      found.set(markerKey, {
        action: match[1],
        task_id: match[2],
        markerKey
      });
    }

    if (found.size === 0) return { marker: null, ambiguous: false };
    if (found.size > 1) return { marker: null, ambiguous: true };
    return { marker: Array.from(found.values())[0], ambiguous: false };
  }

  function completedAssistantCommandCandidate() {
    if (chatIsBusy()) return null;

    const turn = newestAssistantTurn();
    if (!turn) {
      resetCommandTurnTracker();
      return null;
    }

    const text = assistantTurnText(turn);
    const fingerprint = assistantTurnFingerprint(turn, text);
    const now = Date.now();

    if (turn.key !== commandTurnKey || fingerprint !== commandTurnFingerprint) {
      commandTurnKey = turn.key;
      commandTurnFingerprint = fingerprint;
      commandTurnStableSince = now;
      return null;
    }

    // Copy-action normally appears when a turn is complete. If the UI variant
    // does not expose it, the longer stability timer is the fallback.
    const stableFor = now - commandTurnStableSince;
    const minStableMs = assistantTurnHasCopyAction(turn) ? 450 : 1500;
    if (stableFor < minStableMs) return null;

    const parsed = standaloneCommandFromText(text);
    return { ...parsed, turnKey: turn.key, fingerprint };
  }

  async function sendCommand(marker, identity) {'''

src, scanner_count = scanner_pattern.subn(scanner_replacement, src, count=1)
if scanner_count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"scannerblok niet eenduidig gevonden (matches={scanner_count}); backup hersteld")

# Standardize route-conflict behavior. Accept both known old forms.
route_patterns = [
    r"if \(response\.status === 409\) \{ status\(`route conflict \$\{marker\.task_id\}`, true\); return false; \}",
    r"if \(response\.status === 409\) \{ status\(`route conflict genegeerd \$\{marker\.task_id\}`, true\); return 'route_conflict'; \}",
]
route_replacement = "if (response.status === 409) { status(`route conflict genegeerd ${marker.task_id}`, true); return 'route_conflict'; }"
route_done = False
for pattern in route_patterns:
    src, count = re.subn(pattern, route_replacement, src, count=1)
    if count == 1:
        route_done = True
        break
if not route_done:
    shutil.copy2(BACKUP, PATH)
    die("HTTP-409 patchpunt niet gevonden; backup hersteld")

scan_pattern = re.compile(
    r"  async function scanCommands\(\) \{.*?\n  async function setFallbackForCurrentChat\(showAlert\) \{",
    re.S,
)

scan_replacement = r'''  async function scanCommands() {
    if (scanBusy || !enabled() || !token()) return;

    const candidate = completedAssistantCommandCandidate();
    if (!candidate) return;
    if (candidate.ambiguous) {
      status('meerdere commandmarkers in nieuwste assistant-turn; genegeerd', true);
      return;
    }
    if (!candidate.marker) return;

    scanBusy = true;
    try {
      const identity = await ensureTabIdentity();
      if (!identity.stable) {
        status('wacht op vaste ChatGPT chat-ID');
        return;
      }

      const marker = candidate.marker;
      // Task IDs are globally unique by protocol. This also prevents a copied
      // historical marker from being executed again in another chat.
      const dedupeKey = `global|${marker.markerKey}`;
      if (remembered(KEY_COMMAND_IDS, dedupeKey)) return;

      const result = await sendCommand(marker, identity);
      if (result === true) {
        remember(KEY_COMMAND_IDS, dedupeKey);
        status(`command ${marker.action}: ${marker.task_id}`);
      } else if (result === 'route_conflict') {
        remember(KEY_COMMAND_IDS, dedupeKey);
      }
    } catch (_) {
      status('command receiver niet bereikbaar', true);
    } finally {
      scanBusy = false;
    }
  }

  async function setFallbackForCurrentChat(showAlert) {'''

src, scan_count = scan_pattern.subn(scan_replacement, src, count=1)
if scan_count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"scanCommands-blok niet eenduidig gevonden (matches={scan_count}); backup hersteld")

# Remove the expensive full-DOM observer if present. v0.3.4+ may already lack it.
observer_pattern = re.compile(
    r"\n\s*const observer = new MutationObserver\([^\n]*\);\n\s*observer\.observe\([^\n]*\);",
    re.M,
)
src, _ = observer_pattern.subn('', src, count=1)

# Poll a tiny newest-turn state machine rather than the whole transcript.
interval_pattern = re.compile(r"setInterval\(scanCommands,\s*\d+\s*\);")
src, interval_count = interval_pattern.subn("setInterval(scanCommands, 650);", src, count=1)
if interval_count != 1:
    shutil.copy2(BACKUP, PATH)
    die("scanCommands interval niet gevonden; backup hersteld")

# Reset turn-tracking when ChatGPT SPA navigation changes conversation.
handle_pattern = "  async function handleUrlChange() {\n    await ensureTabIdentity(true);"
if handle_pattern in src:
    src = src.replace(
        handle_pattern,
        "  async function handleUrlChange() {\n    resetCommandTurnTracker();\n    await ensureTabIdentity(true);",
        1,
    )
elif "resetCommandTurnTracker();\n    await ensureTabIdentity(true);" not in src:
    shutil.copy2(BACKUP, PATH)
    die("handleUrlChange patchpunt niet gevonden; backup hersteld")

# Update displayed/script version irrespective of the specific 0.3.x source.
src = re.sub(r"^// @version\s+[^\s]+", "// @version      0.4.0", src, count=1, flags=re.M)
src = re.sub(
    r"const SCRIPT_VERSION = '[^']+';",
    "const SCRIPT_VERSION = '0.4.0';",
    src,
    count=1,
)
src = re.sub(r"WSL bridge v[0-9.]+:", "WSL bridge v4.0:", src)

PATH.write_text(src, encoding="utf-8")

print(f"OK: {old_version} -> 0.4.0 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Scanner: newest assistant turn + completion/stability + standalone marker + global dedupe.")
print("Volgende stap: node --check en daarna install_multichat.sh uitvoeren.")
