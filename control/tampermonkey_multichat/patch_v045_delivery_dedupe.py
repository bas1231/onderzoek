#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.4 -> v0.4.5.

Fixes a proven repeat-delivery loop in long ChatGPT conversations.

Root cause:
- v0.4.4 confirms delivery by requiring the number of visible user-turn DOM
  nodes to increase after submit;
- ChatGPT can virtualize/prune old turns, so the visible node count may stay
  constant even though the RESULT_READY message was actually submitted;
- the bridge then leaves the event un-ACKed and sends the same result again.

v0.4.5 makes delivery idempotent:
1. identify result messages by a short unique RESULT_READY task anchor rather
   than comparing the entire (possibly very large) payload;
2. detect a genuinely new newest-user-turn by turn-id/fingerprint, not by node
   count growth;
3. before any retry, scan recent user turns for the same result anchor; if it is
   already visible, ACK the event instead of resubmitting it;
4. remember delivered task_ids as well as event_ids so duplicate outbox events
   for the same completed task are drained without another ChatGPT submission;
5. after a submit reports "unconfirmed", perform one recovery scan before
   allowing any retry.

This intentionally keeps the strict rule that an event is ACKed only when the
same result/task is visible in the ChatGPT conversation (or was already locally
recorded as delivered). It does not add a generic shell, network access, live
trading, wallet actions or paid actions.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v045")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")

if "// @version      0.4.5" in src and "const SCRIPT_VERSION = '0.4.5';" in src:
    print("OK: userscript is al v0.4.5; niets gewijzigd.")
    raise SystemExit(0)

if "// @version      0.4.4" not in src or "const SCRIPT_VERSION = '0.4.4';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.4 als basis. Gevonden:\n" + found)

shutil.copy2(PATH, BACKUP)

# Add a task-level delivered cache next to the existing event-level cache.
needle = "  const KEY_SENT_EVENTS = 'prediction_sent_events_v3';\n"
replacement = (
    needle
    + "  const KEY_SENT_TASKS = 'prediction_sent_tasks_v045';\n"
)
if needle not in src:
    shutil.copy2(BACKUP, PATH)
    die("KEY_SENT_EVENTS-regel niet gevonden; backup hersteld")
src = src.replace(needle, replacement, 1)

# Replace count-based full-payload confirmation with turn-fingerprint + anchor
# confirmation, and add a recovery scanner for already-visible deliveries.
confirm_pattern = re.compile(
    r"  function normalizedChatText\(value\) \{.*?\n"
    r"  async function submitMessage\(text\) \{",
    re.S,
)
confirm_replacement = r'''  function normalizedChatText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function userMessageNodes() {
    try {
      return Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
        .filter(node => node && node.isConnected);
    } catch (_) {
      return [];
    }
  }

  function deliveryAnchor(text) {
    const raw = String(text || '');
    const match = raw.match(/(?:^|\n)RESULT_READY:\s*([A-Za-z0-9._:-]{1,160})(?:\r?\n|$)/);
    if (match) return `RESULT_READY: ${match[1]}`;
    return normalizedChatText(raw).slice(0, 220);
  }

  function userTurnSnapshot() {
    const nodes = userMessageNodes();
    if (!nodes.length) return null;
    const root = nodes[nodes.length - 1];
    const container = root.closest?.(
      '[data-turn-id], [data-testid^="conversation-turn-"], article'
    ) || root;
    const text = String(root.innerText || root.textContent || '');
    const explicitId = String(
      container.getAttribute?.('data-turn-id') ||
      container.getAttribute?.('data-testid') ||
      root.getAttribute?.('data-message-id') ||
      ''
    );
    const normalized = normalizedChatText(text);
    const key = explicitId
      ? `user:${explicitId}`
      : `user-fp:${stableHash(`${normalized.length}|${normalized.slice(-320)}`)}`;
    return { key, text: normalized };
  }

  function turnContainsDelivery(turn, text) {
    if (!turn) return false;
    const anchor = normalizedChatText(deliveryAnchor(text));
    if (!anchor) return false;
    return normalizedChatText(turn.text).includes(anchor);
  }

  function recentUserTurnContainsDelivery(text, limit = 12) {
    const anchor = normalizedChatText(deliveryAnchor(text));
    if (!anchor) return false;
    const nodes = userMessageNodes();
    for (const node of nodes.slice(Math.max(0, nodes.length - limit))) {
      const actual = normalizedChatText(node.innerText || node.textContent || '');
      if (actual.includes(anchor)) return true;
    }
    return false;
  }

  function newUserTurnContains(text, beforeKey) {
    const current = userTurnSnapshot();
    if (!current) return false;
    if (beforeKey && current.key === beforeKey) return false;
    return turnContainsDelivery(current, text);
  }

  async function submitMessage(text) {'''
src, count = confirm_pattern.subn(lambda _m: confirm_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"confirmation-blok niet eenduidig gevonden (matches={count}); backup hersteld")

# v0.4.4 stores a visible-user count before submit. Switch that to a stable
# newest-turn key so DOM virtualization cannot create a false negative.
src, count = re.subn(
    r"    const beforeUserCount = userMessageNodes\(\)\.length;\n",
    "    const beforeUserTurn = userTurnSnapshot();\n    const beforeUserKey = beforeUserTurn ? beforeUserTurn.key : '';\n",
    src,
    count=1,
)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"beforeUserCount-regel niet gevonden (matches={count}); backup hersteld")

src = src.replace(
    "newUserTurnContains(text, beforeUserCount)",
    "newUserTurnContains(text, beforeUserKey)",
)

# Make the wake loop recover idempotently before it ever tries to send the
# same task/result again.
wake_old = '''        if (remembered(KEY_SENT_EVENTS, event.event_id)) {
          await ack(event.event_id, identity.chatId, identity.consumerId);
          continue;
        }

        status(`event ${event.task_id || event.event_id}`);
        const sent = await submitMessage(String(event.message));
        if (!sent) { await sleep(1000); continue; }
        remember(KEY_SENT_EVENTS, event.event_id);
        const ok = await ack(event.event_id, identity.chatId, identity.consumerId);
        status(ok ? `verzonden: ${event.task_id || event.event_id}` : 'ACK mislukt', !ok);'''

wake_new = '''        const taskKey = String(event.task_id || '').trim();
        const alreadyDelivered =
          remembered(KEY_SENT_EVENTS, event.event_id) ||
          (taskKey && remembered(KEY_SENT_TASKS, taskKey)) ||
          recentUserTurnContainsDelivery(String(event.message));

        if (alreadyDelivered) {
          remember(KEY_SENT_EVENTS, event.event_id);
          if (taskKey) remember(KEY_SENT_TASKS, taskKey);
          const ok = await ack(event.event_id, identity.chatId, identity.consumerId);
          status(ok ? `dedupe ACK: ${taskKey || event.event_id}` : 'dedupe ACK mislukt', !ok);
          if (!ok) await sleep(1200);
          continue;
        }

        status(`event ${taskKey || event.event_id}`);
        const sent = await submitMessage(String(event.message));
        if (!sent) {
          // A ChatGPT user turn can be created while DOM virtualization makes
          // the immediate submit proof miss it. Recover once by anchor before
          // permitting any retry.
          if (recentUserTurnContainsDelivery(String(event.message))) {
            remember(KEY_SENT_EVENTS, event.event_id);
            if (taskKey) remember(KEY_SENT_TASKS, taskKey);
            const recovered = await ack(event.event_id, identity.chatId, identity.consumerId);
            status(recovered ? `hersteld + ACK: ${taskKey || event.event_id}` : 'herstel-ACK mislukt', !recovered);
            if (!recovered) await sleep(1200);
            continue;
          }
          await sleep(1000);
          continue;
        }
        remember(KEY_SENT_EVENTS, event.event_id);
        if (taskKey) remember(KEY_SENT_TASKS, taskKey);
        const ok = await ack(event.event_id, identity.chatId, identity.consumerId);
        status(ok ? `verzonden: ${taskKey || event.event_id}` : 'ACK mislukt', !ok);'''

if wake_old not in src:
    shutil.copy2(BACKUP, PATH)
    die("wake delivery-blok niet exact gevonden; backup hersteld")
src = src.replace(wake_old, wake_new, 1)

src = src.replace("// @version      0.4.4", "// @version      0.4.5", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.4';", "const SCRIPT_VERSION = '0.4.5';", 1)
src = src.replace("WSL bridge v4.4:", "WSL bridge v4.5:")

PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.4 -> 0.4.5 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: RESULT_READY anchor + virtualisatiebestendige turn-proof + task/event dedupe + recovery ACK.")
