from __future__ import annotations

from pathlib import Path
import hashlib
import os
import subprocess
import sys

ROOT = Path.cwd()
SOURCE = ROOT / "control/tampermonkey_multichat/prediction-chat-wake.user.js"
RUNTIME = Path.home() / ".local/share/prediction-chat-bridge/prediction-chat-wake.user.js"

TARGETS = [
    "tests/audit/test_delivery_behavior.py",
    "tests/audit/test_reliability_regressions.py",
    "tests/bridge/test_tampermonkey_multichat.py",
    "control/tampermonkey_multichat/test_userscript_delivery_dedupe_static.py",
    "control/tampermonkey_multichat/test_userscript_v046_guard_static.py",
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pre() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    assert "// @version      0.4.8" in text
    assert "const SCRIPT_VERSION = '0.4.8';" in text
    assert "@updateURL    http://localhost:8765/prediction-chat-wake.user.js" in text
    assert "generationChangedAfterDelivery" in text

    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    cp = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *TARGETS],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=420,
    )
    output = cp.stdout or ""
    if len(output) > 12000:
        output = output[-12000:]
    print("ACK_FIX_PYTEST_RC=" + str(cp.returncode), flush=True)
    if output:
        print(output, flush=True)
    if cp.returncode != 0:
        failed = []
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("FAILED "):
                failed.append(stripped.split(" - ", 1)[0])
        print("ACK_FIX_FAILS=" + ("|".join(failed[-12:]) if failed else "NO_FAILED_LINES"), flush=True)
    return cp.returncode

def post() -> int:
    if not RUNTIME.is_file():
        raise SystemExit("ACK_FIX_RUNTIME_MISSING")
    source_sha = sha(SOURCE)
    runtime_sha = sha(RUNTIME)
    text = RUNTIME.read_text(encoding="utf-8")
    assert source_sha == runtime_sha
    assert "// @version      0.4.8" in text
    assert "@updateURL    http://localhost:8765/prediction-chat-wake.user.js" in text
    print("ACK_FIX_RUNTIME=PASS", flush=True)
    print("USERSCRIPT_SHA256=" + runtime_sha, flush=True)
    return 0

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "pre":
        raise SystemExit(pre())
    if mode == "post":
        raise SystemExit(post())
    raise SystemExit("usage: ack_fix_acceptance_e049.py pre|post")
