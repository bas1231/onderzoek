#!/usr/bin/env python3
"""Patch Prediction Chat Wake userscript v0.4.7 -> v0.5.0 active-page presence.

The patch is intentionally narrow and assertion-heavy. It adds authenticated
focused/visible presence heartbeats to the existing command router while
preserving the current delivery, ACK and command-marker behaviour.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TARGET = Path("control/tampermonkey_multichat/prediction-chat-wake.user.js")

PRESENCE_BLOCK = r'''

  let presenceBusy = false;

  async function publishPresence() {
    if (presenceBusy || !enabled() || !token()) return;
    presenceBusy = true;
    try {
      const identity = await ensureTabIdentity();
      if (!identity.stable) return;
      const focused = document.visibilityState === 'visible' && document.hasFocus();
      const response = await gmRequest({
        method: 'POST', url: `${COMMAND_BASE}/presence`, timeout: 5000,
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        data: JSON.stringify({
          chat_id: identity.chatId,
          consumer_id: identity.consumerId,
          focused,
          visible: document.visibilityState === 'visible'
        })
      });
      if (response.status !== 200) throw new Error(`presence HTTP ${response.status}`);
    } catch (_) {
      // Presence is advisory routing state. Delivery/ACK logic remains separate.
    } finally {
      presenceBusy = false;
    }
  }
'''

STARTUP_BLOCK = r'''
    window.addEventListener('focus', () => { publishPresence(); });
    window.addEventListener('blur', () => { publishPresence(); });
    document.addEventListener('visibilitychange', () => { publishPresence(); });
    setInterval(publishPresence, 2000);
'''


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one anchor, got {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


def transform(text: str) -> str:
    if "// @version      0.5.0" in text and "async function publishPresence()" in text:
        return text
    if "// @version      0.4.7" not in text:
        raise RuntimeError("expected userscript v0.4.7 baseline")

    out = text
    out = replace_once(out, "// @version      0.4.7", "// @version      0.5.0")
    out = replace_once(out, "const SCRIPT_VERSION = '0.4.7';", "const SCRIPT_VERSION = '0.5.0';")
    out = replace_once(out, "WSL bridge v4.7:", "WSL bridge v5.0:")

    if "// @updateURL    http://localhost:8765/prediction-chat-wake.user.js" not in out:
        out = replace_once(
            out,
            "// @match        https://chatgpt.com/*",
            "// @match        https://chatgpt.com/*\n"
            "// @updateURL    http://localhost:8765/prediction-chat-wake.user.js\n"
            "// @downloadURL  http://localhost:8765/prediction-chat-wake.user.js",
        )

    menu_anchor = "  GM_registerMenuCommand('Toon chat-ID', async () => {"
    out = replace_once(out, menu_anchor, PRESENCE_BLOCK + "\n" + menu_anchor)

    url_anchor = "      scanCommands();\n      preserveLegacyFallback();"
    out = replace_once(
        out,
        url_anchor,
        "      scanCommands();\n      preserveLegacyFallback();\n      publishPresence();",
    )

    startup_anchor = "    const observer = new MutationObserver(() => { scanCommands(); preserveLegacyFallback(); });"
    out = replace_once(out, startup_anchor, STARTUP_BLOCK + "\n" + startup_anchor)

    identity_anchor = "      preserveLegacyFallback();\n      scanCommands();\n      restartWakeLoop('startup');"
    out = replace_once(
        out,
        identity_anchor,
        "      preserveLegacyFallback();\n      scanCommands();\n      publishPresence();\n      restartWakeLoop('startup');",
    )

    required = [
        "// @version      0.5.0",
        "const SCRIPT_VERSION = '0.5.0';",
        "async function publishPresence()",
        "`${COMMAND_BASE}/presence`",
        "document.hasFocus()",
        "setInterval(publishPresence, 2000)",
        "@updateURL    http://localhost:8765/prediction-chat-wake.user.js",
    ]
    missing = [needle for needle in required if needle not in out]
    if missing:
        raise RuntimeError(f"patch incomplete: {missing}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(TARGET))
    args = parser.parse_args()
    path = Path(args.path)
    original = path.read_text(encoding="utf-8")
    patched = transform(original)
    path.write_text(patched, encoding="utf-8")
    print("USERSCRIPT_ACTIVE_PAGE_V050=PASS")
    print(f"PATH={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
