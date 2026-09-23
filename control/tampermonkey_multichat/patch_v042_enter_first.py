#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.1 -> v0.4.2.

Final-hop send fix based on the working ChatGPT WebUI Bridge pattern:
1. fill the ChatGPT editor;
2. press Enter to submit;
3. wait briefly;
4. only if the editor still contains text, click Send as fallback;
5. ACK only after the exact bridge payload appears as a new user turn.

Routing, WSL execution, command detection and wake polling are unchanged.
'''

from __future__ import annotations

import re
import shutil
from pathlib import Path

PATH = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")
BACKUP = PATH.with_suffix(PATH.suffix + ".pre-v042")


def die(message: str) -> None:
    raise SystemExit(f"STOP: {message}")


if not PATH.is_file(): die(f"userscript niet gevonden: {PATH}")
src = PATH.read_text(encoding="utf-8")
if "// @version      0.4.2" in src and "const SCRIPT_VERSION = '0.4.2';" in src:
    print("OK: userscript is al v0.4.2; niets gewijzigd.")
    raise SystemExit(0)
if "// @version      0.4.1" not in src or "const SCRIPT_VERSION = '0.4.1';" not in src:
    found = "\n".join(line for line in src.splitlines() if "@version" in line or "SCRIPT_VERSION" in line)
    die("verwacht lokale v0.4.1 als basis. Gevonden:\n" + found)
shutil.copy2(PATH, BACKUP)
submit_pattern = re.compile(r"  async function submitMessage\(text\) \{.*?\n  \}\n\n  async function ack\(eventId, chatId, eventConsumerId\) \{", re.S)
submit_replacement = r'''  function composerText(el) {
    if (!el) return '';
    try {
      return String(('value' in el ? el.value : '') || el.innerText || el.textContent || '').trim();
    } catch (_) { return ''; }
  }

  async function submitMessage(text) {
    if (chatIsBusy()) return false;
    const composer = findComposer();
    if (!composer) { status('composer niet gevonden', true); return false; }
    const beforeUserCount = userMessageNodes().length;
    setComposerText(composer, text);
    await sleep(400);
    try {
      composer.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
      }));
    } catch (_) {}
    for (let i = 0; i < 20; i += 1) {
      if (newUserTurnContains(text, beforeUserCount)) return true;
      await sleep(100);
    }
    if (composerText(findComposer()) !== '') {
      let button = null;
      for (let i = 0; i < 20; i += 1) {
        button = findSendButton();
        if (button) break;
        await sleep(100);
      }
      if (button) button.click(); else status('sendknop niet actief na Enter', true);
    }
    for (let i = 0; i < 100; i += 1) {
      if (newUserTurnContains(text, beforeUserCount)) return true;
      await sleep(100);
    }
    status('verzenden niet bevestigd in chat; geen ACK', true);
    return false;
  }

  async function ack(eventId, chatId, eventConsumerId) {'''
src, count = submit_pattern.subn(lambda _m: submit_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"submitMessage-blok niet eenduidig gevonden (matches={count}); backup hersteld")
src = src.replace("// @version      0.4.1", "// @version      0.4.2", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.1';", "const SCRIPT_VERSION = '0.4.2';", 1)
src = src.replace("WSL bridge v4.1:", "WSL bridge v4.2:")
PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.1 -> 0.4.2 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Send-pad: Enter-first, click-fallback, echte user-turn vereist vóór ACK.")
