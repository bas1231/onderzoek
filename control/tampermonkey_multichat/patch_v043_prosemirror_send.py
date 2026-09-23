#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.2 -> v0.4.3.

Fixes only the final ChatGPT composer/send hop.

Why:
- v0.4.2 proves routing + WSL + outbox are good, but ChatGPT still does not
  create a new user turn.
- The reliable current ChatGPT userscript pattern is:
  focus composer -> execCommand(selectAll/insertText) -> if DOM text does not
  match, rebuild ProseMirror paragraphs -> dispatch InputEvent -> wait until
  the actual Send button is enabled -> click it -> confirm a new user turn.

This patch leaves routing, command detection, wake polling and ACK rules intact.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v043")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file(): die(f"userscript niet gevonden: {PATH}")
src = PATH.read_text(encoding="utf-8")
if "// @version      0.4.3" in src and "const SCRIPT_VERSION = '0.4.3';" in src:
    print("OK: userscript is al v0.4.3; niets gewijzigd.")
    raise SystemExit(0)
if "// @version      0.4.2" not in src or "const SCRIPT_VERSION = '0.4.2';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.2 als basis. Gevonden:\n" + found)
shutil.copy2(PATH, BACKUP)
set_pattern = re.compile(r"  function setComposerText\(el, text\) \{.*?\n  \}\n\n", re.S)
set_replacement = r'''  function rawComposerText(el) {
    if (!el) return '';
    try {
      if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) return String(el.value || '');
      return String(el.innerText || el.textContent || '');
    } catch (_) { return ''; }
  }

  function setComposerText(el, text) {
    const wanted = String(text || '');
    el.focus();
    if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (setter) setter.call(el, wanted); else el.value = wanted;
      try {
        el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: wanted }));
      } catch (_) { el.dispatchEvent(new Event('input', { bubbles: true })); }
      return rawComposerText(el).trim() === wanted.trim();
    }
    let inserted = false;
    try {
      document.execCommand('selectAll', false, null);
      inserted = document.execCommand('insertText', false, wanted);
    } catch (_) {}
    if (!inserted || rawComposerText(el) !== wanted) {
      try {
        el.innerHTML = '';
        const lines = wanted.split('\n');
        for (const line of lines) {
          const p = document.createElement('p');
          if (line.length === 0) p.appendChild(document.createElement('br'));
          else p.textContent = line;
          el.appendChild(p);
        }
      } catch (_) { el.textContent = wanted; }
    }
    try {
      el.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: wanted }));
    } catch (_) { el.dispatchEvent(new Event('input', { bubbles: true })); }
    return rawComposerText(el) === wanted;
  }

'''
src, count = set_pattern.subn(lambda _m: set_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"setComposerText-blok niet eenduidig gevonden (matches={count}); backup hersteld")
submit_pattern = re.compile(r"  async function submitMessage\(text\) \{.*?\n  \}\n\n  async function ack\(eventId, chatId, eventConsumerId\) \{", re.S)
submit_replacement = r'''  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    const beforeUserCount = userMessageNodes().length;
    const filled = setComposerText(composer, text);
    if (!filled) { status('composer vullen niet bevestigd', true); return false; }
    let button = null;
    for (let i = 0; i < 80; i += 1) {
      button = findSendButton();
      if (button) break;
      await sleep(100);
    }
    if (!button) { status('sendknop blijft uitgeschakeld', true); return false; }
    button.click();
    for (let i = 0; i < 150; i += 1) {
      if (newUserTurnContains(text, beforeUserCount)) return true;
      await sleep(100);
    }
    status('klik verstuurd maar geen nieuwe user-turn; geen ACK', true);
    return false;
  }

  async function ack(eventId, chatId, eventConsumerId) {'''
src, count = submit_pattern.subn(lambda _m: submit_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"submitMessage-blok niet eenduidig gevonden (matches={count}); backup hersteld")
src = src.replace("// @version      0.4.2", "// @version      0.4.3", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.2';", "const SCRIPT_VERSION = '0.4.3';", 1)
src = src.replace("WSL bridge v4.2:", "WSL bridge v4.3:")
PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.2 -> 0.4.3 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: ProseMirror-vulling + echte enabled Send-click + user-turn bevestiging.")
