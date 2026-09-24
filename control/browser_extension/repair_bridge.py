from __future__ import annotations

from pathlib import Path
import json
import shutil
import time

from patch_result_ack_presend_gate import MARKER as ACK_GATE_MARKER
from patch_result_ack_presend_gate import patch_text as patch_ack_presend_gate

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "control" / "browser_extension"
CONTENT = EXT / "content.js"
MANIFEST = EXT / "manifest.json"


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(path.name + f".bak-{stamp}")
    shutil.copy2(path, target)
    return target


def _assert_existing_bridge_invariants(text: str) -> None:
    required = (
        "async function flushDurableQueue()",
        "async function resultAckPending(taskId)",
        "async function flushPendingResultAcks()",
        "const CONTENT_VERSION =",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(
            "Refusing repair: audited bridge invariants missing: "
            + ", ".join(missing)
        )


def patch_content() -> tuple[bool, list[Path]]:
    """Apply only forward/idempotent repairs; never downgrade local code."""
    original = CONTENT.read_text(encoding="utf-8")
    _assert_existing_bridge_invariants(original)

    try:
        patched, changed = patch_ack_presend_gate(original)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    backups: list[Path] = []
    if changed:
        backups.append(backup(CONTENT))
        CONTENT.write_text(patched, encoding="utf-8")

    final = CONTENT.read_text(encoding="utf-8")
    _assert_existing_bridge_invariants(final)
    if ACK_GATE_MARKER not in final:
        raise SystemExit("Repair failed: result ACK pre-send gate missing")

    return changed, backups


def validate_manifest() -> tuple[bool, list[Path]]:
    """Validate manifest only. Never rewrite/downgrade a newer local version."""
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    version = str(data.get("version") or "").strip()
    if not version:
        raise SystemExit("Refusing repair: manifest version missing")
    return False, []


def main() -> None:
    if not CONTENT.exists() or not MANIFEST.exists():
        raise SystemExit("Run this from the prediction_research checkout")

    content_changed, content_backups = patch_content()
    manifest_changed, manifest_backups = validate_manifest()

    print("PREDICTION_BRIDGE_REPAIR_OK")
    print("content_changed=", content_changed)
    print("manifest_changed=", manifest_changed)
    print("ack_presend_gate=present")
    for path in content_backups + manifest_backups:
        print("backup=", path)
    print("runtime_liveness=UNVERIFIED")


if __name__ == "__main__":
    main()
