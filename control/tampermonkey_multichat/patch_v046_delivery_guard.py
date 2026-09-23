#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.5 -> v0.4.6.

Stops repeat RESULT_READY dumps even when ChatGPT's DOM shape changes.

Changes:
- broaden user-turn selectors;
- add page-level RESULT_READY anchor detection as a DOM-schema fallback;
- never overwrite a non-empty composer;
- add an in-memory retry cooldown after an unconfirmed submit;
- before every retry, re-check whether the same RESULT_READY task is already
  visible anywhere on the current ChatGPT page and ACK instead of resending.

The bridge remains fail-closed: no generic shell, no live trading, wallet or
paid actions are introduced.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v046")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")
if "// @version      0.4.6" in src and "const SCRIPT_VERSION = '0.4.6';" in src:
    print("OK: userscript is al v0.4.6; niets gewijzigd.")
    raise SystemExit(0)
if "// @version      0.4.5" not in src or "const SCRIPT_VERSION = '0.4.5';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.5 als basis. Gevonden:\n" + found)

shutil.copy2(PATH, BACKUP)

# Broaden user turn discovery and add page-level anchor fallback.
old = r'''  function userMessageNodes() {
    try {
      return Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
        .filter(node => node && node.isConnected);
    } catch (_) {
      return [];
    }
  }
'''
new = r'''  function userMessageNodes() {
    try {
      const selectors = [
        '[data-message-author-role="user"]',
        'article[data-turn="user"]',
        'article[data-turn-id][data-turn="user"]'
      ];
      const out = [];
      const seen = new Set();
      for (const selector of selectors) {
        for (const node of document.querySelectorAll(selector)) {
          if (!node || !node.isConnected || seen.has(node)) continue;
          seen.add(node);
          out.push(node);
        }
      }
      return out;
    } catch (_) {
      return [];
    }
  }
'''
if old not in src:
    shutil.copy2(BACKUP, PATH)
    die("userMessageNodes-blok niet exact gevonden; backup hersteld")
src = src.replace(old, new, 1)

needle = r'''  function recentUserTurnContainsDelivery(text, limit = 12) {
    const anchor = normalizedChatText(deliveryAnchor(text));
    if (!anchor) return false;
    const nodes = userMessageNodes();
    for (const node of nodes.slice(Math.max(0, nodes.length - limit))) {
      const actual = normalizedChatText(node.innerText || node.textContent || '');
      if (actual.includes(anchor)) return true;
    }
    return false;
  }
'''
replacement = r'''  function pageContainsDelivery(text) {
    const anchor = normalizedChatText(deliveryAnchor(text));
    if (!anchor) return false;
    try {
      const bodyText = normalizedChatText(document.body?.innerText || document.documentElement?.innerText || '');
      return bodyText.includes(anchor);
    } catch (_) {
      return false;
    }
  }

  function recentUserTurnContainsDelivery(text, limit = 20) {
    const anchor = normalizedChatText(deliveryAnchor(text));
    if (!anchor) return false;
    const nodes = userMessageNodes();
    for (const node of nodes.slice(Math.max(0, nodes.length - limit))) {
      const actual = normalizedChatText(node.innerText || node.textContent || '');
      if (actual.includes(anchor)) return true;
    }
    return pageContainsDelivery(text);
  }
'''
if needle not in src:
    shutil.copy2(BACKUP, PATH)
    die("recentUserTurnContainsDelivery-blok niet exact gevonden; backup hersteld")
src = src.replace(needle, replacement, 1)

# Refuse to overwrite anything the user has already typed.
submit_needle = "    const composer = findComposer();\n    if (!composer) { status('composer niet gevonden', true); return false; }\n"
submit_repl = submit_needle + "    const existingComposerText = normalizedChatText(rawComposerText(composer));\n    if (existingComposerText) { status('composer niet leeg; bridge wacht', true); return false; }\n    if (pageContainsDelivery(text)) return true;\n"
if submit_needle not in src:
    shutil.copy2(BACKUP, PATH)
    die("submit composer-blok niet gevonden; backup hersteld")
src = src.replace(submit_needle, submit_repl, 1)

# Add a runtime cooldown map so a changed DOM cannot create a rapid resend storm.
state_needle = "  let wakeGeneration = 0;\n"
state_repl = state_needle + "  const deliveryRetryAfter = new Map();\n"
if state_needle not in src:
    shutil.copy2(BACKUP, PATH)
    die("wakeGeneration-regel niet gevonden; backup hersteld")
src = src.replace(state_needle, state_repl, 1)

wake_needle = "        status(`event ${taskKey || event.event_id}`);\n        const sent = await submitMessage(String(event.message));\n"
wake_repl = "        const retryKey = taskKey || String(event.event_id);\n        const retryAt = Number(deliveryRetryAfter.get(retryKey) || 0);\n        if (Date.now() < retryAt) {\n          status(`delivery hold: ${retryKey}`);\n          await sleep(1200);\n          continue;\n        }\n\n        status(`event ${taskKey || event.event_id}`);\n        deliveryRetryAfter.set(retryKey, Date.now() + 60000);\n        const sent = await submitMessage(String(event.message));\n"
if wake_needle not in src:
    shutil.copy2(BACKUP, PATH)
    die("wake submit-blok niet gevonden; backup hersteld")
src = src.replace(wake_needle, wake_repl, 1)

# Once delivery is confirmed/recovered, clear the hold immediately.
src = src.replace(
    "            remember(KEY_SENT_EVENTS, event.event_id);\n            if (taskKey) remember(KEY_SENT_TASKS, taskKey);\n            const recovered = await ack(event.event_id, identity.chatId, identity.consumerId);",
    "            remember(KEY_SENT_EVENTS, event.event_id);\n            if (taskKey) remember(KEY_SENT_TASKS, taskKey);\n            deliveryRetryAfter.delete(taskKey || String(event.event_id));\n            const recovered = await ack(event.event_id, identity.chatId, identity.consumerId);",
    1,
)
src = src.replace(
    "        remember(KEY_SENT_EVENTS, event.event_id);\n        if (taskKey) remember(KEY_SENT_TASKS, taskKey);\n        const ok = await ack(event.event_id, identity.chatId, identity.consumerId);",
    "        remember(KEY_SENT_EVENTS, event.event_id);\n        if (taskKey) remember(KEY_SENT_TASKS, taskKey);\n        deliveryRetryAfter.delete(taskKey || String(event.event_id));\n        const ok = await ack(event.event_id, identity.chatId, identity.consumerId);",
    1,
)

src = src.replace("// @version      0.4.5", "// @version      0.4.6", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.5';", "const SCRIPT_VERSION = '0.4.6';", 1)
src = src.replace("WSL bridge v4.5:", "WSL bridge v4.6:")

PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.5 -> 0.4.6 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: robuuste user-turn detectie + page-anchor fallback + composer guard + 60s retry hold.")
