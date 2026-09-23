from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "control" / "browser_extension" / "content.js"

OLD = '''      sendingResult = true;

      const sent = await insertAndSend(
        resultMessage(item)
      );'''

NEW = '''      sendingResult = true;

      /*
       * RESULT-ACK-PRESEND-GATE:
       * A result can already have been inserted into ChatGPT while its
       * durable /ack is still retrying. /outbox may therefore expose the
       * same task again after a browser/content-script restart. Never send
       * that task a second time while its durable ACK is pending.
       */
      if (
        await resultAckPending(item.task_id)
      ) {
        console.log(
          "[Prediction Bridge] suppressing result replay; ACK pending:",
          item.task_id
        );
        await flushPendingResultAcks();
        return;
      }

      const sent = await insertAndSend(
        resultMessage(item)
      );'''

MARKER = "RESULT-ACK-PRESEND-GATE"


def patch_text(text: str) -> tuple[str, bool]:
    if MARKER in text:
        return text, False
    if OLD not in text:
        raise ValueError(
            "Refusing to patch: audited pollOutbox anchor not found"
        )
    patched = text.replace(OLD, NEW, 1)
    if patched.count(MARKER) != 1:
        raise ValueError("Patch invariant failed")
    return patched, True


def main() -> int:
    if not TARGET.exists():
        print(f"missing target: {TARGET}", file=sys.stderr)
        return 2
    original = TARGET.read_text(encoding="utf-8")
    try:
        patched, changed = patch_text(original)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    if changed:
        TARGET.write_text(patched, encoding="utf-8")
    print("RESULT_ACK_PRESEND_GATE_OK")
    print(f"changed={str(changed).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
