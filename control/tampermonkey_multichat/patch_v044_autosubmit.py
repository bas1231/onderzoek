#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.3 -> v0.4.4.

Fixes the last browser hop when the bridge can fill the ChatGPT composer but
cannot submit it automatically.  v0.4.4 keeps the strict ACK rule: an outbox
event is acknowledged only after the exact payload appears as a new user turn.

Submit order:
1. fill/verify the composer using the existing v0.4.3 logic;
2. find the send button, preferring the composer form's submit button;
3. use native HTMLFormElement.requestSubmit when possible;
4. fall back to pointer/mouse activation + click();
5. only as a final fallback dispatch Enter key events;
6. confirm an exact new user turn before ACK.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v044")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file():
    die(f"userscript niet gevonden: {PATH}")

src = PATH.read_text(encoding="utf-8")
if "// @version      0.4.4" in src and "const SCRIPT_VERSION = '0.4.4';" in src:
    print("OK: userscript is al v0.4.4; niets gewijzigd.")
    raise SystemExit(0)

if "// @version      0.4.3" not in src or "const SCRIPT_VERSION = '0.4.3';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.3 als basis. Gevonden:\n" + found)

shutil.copy2(PATH, BACKUP)

find_pattern = re.compile(r"  function findSendButton\(\) \{.*?\n  \}\n\n", re.S)
find_replacement = r'''  function findSendButton(composer = null) {
    const c = composer || findComposer();
    try {
      const form = c && c.closest ? c.closest('form') : null;
      if (form) {
        const local = form.querySelector('button[type="submit"], [data-testid="send-button"], #composer-submit-button');
        if (local && local.offsetParent !== null && !local.disabled && local.getAttribute('aria-disabled') !== 'true') return local;
      }
    } catch (_) {}
    const selectors = [
      '[data-testid="send-button"]', '#composer-submit-button', 'button[type="submit"]',
      'button[aria-label="Send prompt"]', 'button[aria-label*="Send"]',
      'button[aria-label*="Verstuur"]', 'button[aria-label*="Verzend"]'
    ];
    for (const selector of selectors) {
      const nodes = document.querySelectorAll(selector);
      for (const el of nodes) {
        if (el && el.offsetParent !== null && !el.disabled && el.getAttribute('aria-disabled') !== 'true') return el;
      }
    }
    return null;
  }

'''
src, count = find_pattern.subn(lambda _m: find_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"findSendButton-blok niet eenduidig gevonden (matches={count}); backup hersteld")

submit_pattern = re.compile(r"  async function submitMessage\(text\) \{.*?\n  \}\n\n  async function ack\(eventId, chatId, eventConsumerId\) \{", re.S)
submit_replacement = r'''  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    const beforeUserCount = userMessageNodes().length;
    const filled = setComposerText(composer, text);
    if (!filled) { status('composer vullen niet bevestigd', true); return false; }

    const seen = async (loops, delay = 100) => {
      for (let i = 0; i < loops; i += 1) {
        if (newUserTurnContains(text, beforeUserCount)) return true;
        await sleep(delay);
      }
      return false;
    };

    let button = null;
    for (let i = 0; i < 80; i += 1) {
      button = findSendButton(composer);
      if (button) break;
      await sleep(100);
    }
    if (!button) { status('sendknop blijft uitgeschakeld', true); return false; }

    // Preferred path: browser-native form submission. This avoids relying on a
    // framework-specific click handler and mirrors a real submit activation.
    try {
      const form = composer.closest ? composer.closest('form') : null;
      if (form && typeof form.requestSubmit === 'function') {
        try { HTMLFormElement.prototype.requestSubmit.call(form, button); }
        catch (_) { form.requestSubmit(button); }
        if (await seen(25)) return true;
      }
    } catch (_) {}

    // Fallback: activate the real enabled send button through the normal
    // pointer/mouse event sequence and click activation behaviour.
    try {
      button.focus();
      try { button.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true })); } catch (_) {}
      try { button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window, button: 0 })); } catch (_) {}
      try { button.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerType: 'mouse', isPrimary: true })); } catch (_) {}
      try { button.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window, button: 0 })); } catch (_) {}
      button.click();
      if (await seen(25)) return true;
    } catch (_) {}

    // Last fallback. Some ChatGPT editor builds handle Enter at the editor even
    // when the submit-button activation path changes.
    try {
      composer.focus();
      for (const type of ['keydown', 'keypress', 'keyup']) {
        composer.dispatchEvent(new KeyboardEvent(type, {
          key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
          bubbles: true, cancelable: true
        }));
      }
      if (await seen(40)) return true;
    } catch (_) {}

    status('payload staat in composer maar autosubmit faalde; geen ACK', true);
    return false;
  }

  async function ack(eventId, chatId, eventConsumerId) {'''
src, count = submit_pattern.subn(lambda _m: submit_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"submitMessage-blok niet eenduidig gevonden (matches={count}); backup hersteld")

src = src.replace("// @version      0.4.3", "// @version      0.4.4", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.3';", "const SCRIPT_VERSION = '0.4.4';", 1)
src = src.replace("WSL bridge v4.3:", "WSL bridge v4.4:")

PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.3 -> 0.4.4 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: requestSubmit -> button activation -> Enter fallback; ACK blijft exact-user-turn gated.")
