#!/usr/bin/env python3
'''Patch Prediction Chat Wake Bridge v0.4.4 -> v0.4.5.

Fixes false-negative composer verification in ChatGPT ProseMirror. v0.4.4 can
visibly place the payload in the composer but reject it because innerText for
paragraph blocks may contain browser-inserted blank lines / zero-width chars.

v0.4.5 compares a canonical logical editor value instead:
- CRLF -> LF
- NBSP -> normal space
- zero-width formatting chars removed
- top-level ProseMirror block nodes joined with exactly one newline
- only trailing editor artifact newlines are ignored

The strict safety invariant remains unchanged: the outbox event is ACKed only
after the exact bridge payload is observed as a new user turn.
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

raw_pattern = re.compile(r"  function rawComposerText\(el\) \{.*?\n  \}\n\n", re.S)
raw_replacement = r'''  function normalizeComposerText(value) {
    return String(value == null ? '' : value)
      .replace(/\r\n?/g, '\n')
      .replace(/\u00a0/g, ' ')
      .replace(/[\u200b\u200c\u200d\ufeff]/g, '')
      .replace(/\n+$/g, '');
  }

  function rawComposerText(el) {
    if (!el) return '';
    try {
      if (el instanceof HTMLTextAreaElement || el instanceof HTMLInputElement) {
        return normalizeComposerText(el.value || '');
      }

      // ProseMirror commonly represents each logical line as a top-level block.
      // innerText may insert an extra blank line between those blocks, so derive
      // the logical value from the block nodes themselves when possible.
      const children = Array.from(el.children || []);
      if (children.length) {
        const blockTexts = children.map(child => {
          const text = String(child.innerText || child.textContent || '');
          return normalizeComposerText(text);
        });
        return normalizeComposerText(blockTexts.join('\n'));
      }

      return normalizeComposerText(el.innerText || el.textContent || '');
    } catch (_) { return ''; }
  }

'''
src, count = raw_pattern.subn(lambda _m: raw_replacement, src, count=1)
if count != 1:
    shutil.copy2(BACKUP, PATH)
    die(f"rawComposerText-blok niet eenduidig gevonden (matches={count}); backup hersteld")

src = src.replace(
    "return rawComposerText(el).trim() === wanted.trim();",
    "return rawComposerText(el) === normalizeComposerText(wanted);",
    1,
)
src = src.replace(
    "if (!inserted || rawComposerText(el) !== wanted) {",
    "if (!inserted || rawComposerText(el) !== normalizeComposerText(wanted)) {",
    1,
)
src = src.replace(
    "return rawComposerText(el) === wanted;",
    "return rawComposerText(el) === normalizeComposerText(wanted);",
    1,
)

src = src.replace("// @version      0.4.4", "// @version      0.4.5", 1)
src = src.replace("const SCRIPT_VERSION = '0.4.4';", "const SCRIPT_VERSION = '0.4.5';", 1)
src = src.replace("WSL bridge v4.4:", "WSL bridge v4.5:")

PATH.write_text(src, encoding="utf-8")
print(f"OK: 0.4.4 -> 0.4.5 geschreven: {PATH}")
print(f"Backup: {BACKUP}")
print("Fix: canonieke ProseMirror composer-verificatie; autosubmit/ACK-regels ongewijzigd.")
