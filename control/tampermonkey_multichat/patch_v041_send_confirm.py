#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.0 -> v0.4.1.

Fixes the proven final-hop bug:
- do not treat aria-disabled send buttons as usable;
- after clicking Send, do NOT ACK merely because the composer cleared;
- confirm that a NEW user turn containing the exact bridge result actually
  appeared in this ChatGPT conversation;
- if confirmation fails, leave the wake event un-ACKed so it can retry.

This patch touches only browser-side send confirmation. Routing, command
detection, wake polling and WSL execution remain unchanged.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v041")


def die(msg: str) -> None:
    raise SystemExit(f"STOP: {msg}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")

if "// @version      0.4.1" in src and "const SCRIPT_VERSION = '0.4.1';" in src:
    print("OK: userscript is al v0.4.1; niets gewijzigd.")
    raise SystemExit(0)

if "// @version      0.4.0" not in src or "const SCRIPT_VERSION = '0.4.0';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.0 als basis. Gevonden:\n" + found)

shutil.copy2(PATH, BACKUP)

send_button_pattern = re.compile(r"  function findSendButton\(\) \{.*?\n  \}\n\n  function chatIsBusy\(\)", re.S)
send_button_replacement = r'''  function findSendButton() {
    const selectors = [
      '[data-testid="send-button"]', '#composer-submit-button',
      'button[aria-label="Send prompt"]', 'button[aria-label*="Send"]'
    ];
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (!el || el.offsetParent === null) continue;
      if (el.disabled) continue;
      if (String(el.getAttribute?.('aria-disabled') || '').toLowerCase() === 'true') continue;
      return el;
    }
    return null;
  }

  function chatIsBusy()'''
src, n = send_button_pattern.subn(lambda _m: send_button_replacement, src, count=1)
if n != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"findSendButton niet eenduidig gevonden (matches={n}); backup hersteld")

submit_pattern = re.compile(r"  async function submitMessage\(text\) \{.*?\n  \}\n\n  async function ack\(eventId, chatId, eventConsumerId\) \{", re.S)
submit_replacement = r'''  function normalizedChatText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  function userMessageNodes() {
    try {
      return Array.from(document.querySelectorAll('[data-message-author-role="user"]')).filter(node => node && node.isConnected);
    } catch (_) {
      return [];
    }
  }

  function newUserTurnContains(text, beforeCount) {
    const expected = normalizedChatText(text);
    if (!expected) return false;
    const nodes = userMessageNodes();
    if (nodes.length <= beforeCount) return false;
    for (const node of nodes.slice(beforeCount)) {
      const actual = normalizedChatText(node.innerText || node.textContent || '');
      if (!actual) continue;
      if (actual === expected || actual.includes(expected) || expected.includes(actual)) return true;
    }
    return false;
  }

  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    const beforeUserCount = userMessageNodes().length;
    setComposerText(composer, text);
    let button = null;
    for (let i = 0; i < 40; i += 1) {
      button = findSendButton();
      if (button) break;
      await sleep(100);
    }
    if (!button) { status('sendknop niet actief', true); return false; }
    button.click();
    for (let i = 0; i < 120; i += 1) {
      if (newUserTurnContains(text, beforeUserCount)) return true;
      await sleep(100);
    }
    status('verzenden niet bevestigd in chat; geen ACK', true);
    return false;
  }

  async function ack(eventId, chatId, eventConsumerId) {'''
src, n = submit_pattern.subn(lambda _m: submit_replacement, src, count=1)
if n != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"submitMessage niet eenduidig gevonden (matches={n}); backup hersteld")

src = src.replace("// @version      0.4.0", "// @version      0.4.1", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.0';", "const SCRIPT_VERSION = '0.4.1';", 1)
src = src.replace("WSL bridge v4.0:", "WSL bridge v4.1:")
PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.0 -> 0.4.1 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: aria-disabled sendknop + echte user-turn bevestiging vóór ACK.")
