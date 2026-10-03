from __future__ import annotations

from pathlib import Path
import json
import subprocess
import time

RUNTIME = Path.home() / ".local/share/prediction-chat-bridge"

def main() -> int:
    cp = subprocess.run(
        ["journalctl","--user","-u","prediction-chat-wake.service","-n","1000","--no-pager"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=30,
    )
    lines = (cp.stdout or "").splitlines()
    ack = [x for x in lines if "POST /ack" in x]
    ack_200 = [x for x in ack if '" 200 ' in x or " 200 -" in x]
    ack_503 = [x for x in ack if '" 503 ' in x or " 503 -" in x]
    hook_failed = [x for x in lines if "ack_hook_failed" in x]

    now = time.time()
    def recent(folder: str, seconds: int = 1800):
        p = RUNTIME / folder
        out = []
        if p.is_dir():
            for item in p.glob("*.json"):
                try:
                    age = now - item.stat().st_mtime
                except OSError:
                    continue
                if age <= seconds:
                    out.append((item.name, round(age, 1)))
        return sorted(out, key=lambda x: x[1])[:30]

    result = {
        "journal_rc": cp.returncode,
        "ack_requests": len(ack),
        "ack_200": len(ack_200),
        "ack_503": len(ack_503),
        "ack_hook_failed_lines": len(hook_failed),
        "last_ack_lines": ack[-8:],
        "recent_inflight": recent("inflight"),
        "recent_sent": recent("sent"),
    }
    print("ACK_RUNTIME_DIAG=" + json.dumps(result, sort_keys=True), flush=True)
    return 0 if cp.returncode == 0 else 3

if __name__ == "__main__":
    raise SystemExit(main())
