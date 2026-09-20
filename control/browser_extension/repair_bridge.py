from __future__ import annotations

from pathlib import Path
import json
import shutil
import time

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "control" / "browser_extension"
CONTENT = EXT / "content.js"
MANIFEST = EXT / "manifest.json"

ANCHOR = '''    async function removeDurableEnvelope(taskId) {
      const queue = await loadDurableQueue();

      if (queue[taskId]) {
        delete queue[taskId];
        await saveDurableQueue(queue);
      }
    }


  async function scanForTasks() {'''

FLUSH = r'''    async function removeDurableEnvelope(taskId) {
      const queue = await loadDurableQueue();

      if (queue[taskId]) {
        delete queue[taskId];
        await saveDurableQueue(queue);
      }
    }

    async function flushDurableQueue() {
      if (!(await isArmed())) {
        return;
      }

      const queue = await loadDurableQueue();
      const processed = new Set(
        await processedTaskIds()
      );

      let changed = false;
      const now = Date.now();

      for (const [taskId, record] of Object.entries(queue)) {
        if (
          !record ||
          typeof record !== "object" ||
          !record.envelope
        ) {
          delete queue[taskId];
          changed = true;
          continue;
        }

        if (processed.has(taskId)) {
          delete queue[taskId];
          changed = true;
          continue;
        }

        const attempts = Number(record.attempts || 0);
        const lastAttemptAt = Number(record.lastAttemptAt || 0);
        const backoffMs = Math.min(
          60000,
          2000 * Math.pow(2, Math.min(attempts, 5))
        );

        if (
          lastAttemptAt &&
          now - lastAttemptAt < backoffMs
        ) {
          continue;
        }

        record.attempts = attempts + 1;
        record.lastAttemptAt = now;
        record.updatedAt = now;

        try {
          const discoverResponse = await bridgeFetch(
            "/discover",
            "POST",
            {
              task_id: taskId
            }
          );

          if (
            !discoverResponse ||
            !discoverResponse.ok
          ) {
            record.lastError =
              "discover: " +
              JSON.stringify(discoverResponse).slice(0, 500);
            changed = true;
            continue;
          }

          const response = await bridgeFetch(
            "/enqueue",
            "POST",
            record.envelope
          );

          if (response && response.ok) {
            await markTaskProcessed(taskId);
            processed.add(taskId);
            delete queue[taskId];
            changed = true;

            console.log(
              "[Prediction Bridge] durable task accepted:",
              taskId,
              response.status
            );
          } else {
            record.lastError =
              "enqueue: " +
              JSON.stringify(response).slice(0, 500);
            changed = true;
          }
        } catch (error) {
          record.lastError = String(error).slice(0, 500);
          changed = true;

          console.warn(
            "[Prediction Bridge] durable retry failed:",
            taskId,
            error
          );
        }
      }

      if (changed) {
        await saveDurableQueue(queue);
      }
    }


  async function scanForTasks() {'''

OLD_GUARD = '''(() => {
  if (window.__PREDICTION_RESEARCH_BRIDGE_LOADED__) {
    return;
  }

  window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ = true;
'''

NEW_GUARD = '''(() => {
  const CONTENT_VERSION = "0.5.2";

  if (
    window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ ===
    CONTENT_VERSION
  ) {
    return;
  }

  window.__PREDICTION_RESEARCH_BRIDGE_LOADED__ =
    CONTENT_VERSION;
'''


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(path.name + f".bak-{stamp}")
    shutil.copy2(path, target)
    return target


def patch_content() -> tuple[bool, list[Path]]:
    text = CONTENT.read_text(encoding="utf-8")
    backups: list[Path] = []
    changed = False

    if "async function flushDurableQueue()" not in text:
        if ANCHOR not in text:
            raise SystemExit(
                "Refusing to patch: durable-queue anchor not found. "
                "Repository content differs from the audited version."
            )
        backups.append(backup(CONTENT))
        text = text.replace(ANCHOR, FLUSH, 1)
        changed = True

    if OLD_GUARD in text:
        if not backups:
            backups.append(backup(CONTENT))
        text = text.replace(OLD_GUARD, NEW_GUARD, 1)
        changed = True

    if changed:
        CONTENT.write_text(text, encoding="utf-8")

    final = CONTENT.read_text(encoding="utf-8")
    if "async function flushDurableQueue()" not in final:
        raise SystemExit("Repair failed: flushDurableQueue is still missing")
    if 'const CONTENT_VERSION = "0.5.2";' not in final:
        raise SystemExit("Repair failed: versioned reinjection guard is missing")

    return changed, backups


def patch_manifest() -> tuple[bool, list[Path]]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("version") == "0.5.2":
        return False, []

    backups = [backup(MANIFEST)]
    data["version"] = "0.5.2"
    MANIFEST.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True, backups


def main() -> None:
    if not CONTENT.exists() or not MANIFEST.exists():
        raise SystemExit("Run this from the prediction_research checkout")

    content_changed, content_backups = patch_content()
    manifest_changed, manifest_backups = patch_manifest()

    print("PREDICTION_BRIDGE_REPAIR_OK")
    print("content_changed=", content_changed)
    print("manifest_changed=", manifest_changed)
    for path in content_backups + manifest_backups:
        print("backup=", path)
    print("next=reload Prediction Research Bridge once in chrome://extensions")


if __name__ == "__main__":
    main()
