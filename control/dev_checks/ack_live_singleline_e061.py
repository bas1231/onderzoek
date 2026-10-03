from __future__ import annotations
from pathlib import Path
import re
import subprocess
import time

RUNTIME=Path.home()/".local/share/prediction-chat-bridge"
SCRIPT=RUNTIME/"prediction-chat-wake.user.js"

def main():
    version="MISSING"
    if SCRIPT.is_file():
        text=SCRIPT.read_text(encoding="utf-8",errors="replace")
        m=re.search(r"// @version\s+([0-9.]+)",text)
        if m:
            version=m.group(1)

    cp=subprocess.run(
        ["journalctl","--user","-u","prediction-chat-wake.service","-n","500","--no-pager"],
        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,timeout=30
    )
    lines=(cp.stdout or "").splitlines()
    ack=[x for x in lines if "POST /ack" in x]
    last=ack[-1] if ack else "NONE"
    now=time.time()
    def recent_count(name):
        p=RUNTIME/name
        n=0
        if p.is_dir():
            for f in p.glob("*.json"):
                try:
                    if now-f.stat().st_mtime <= 600:
                        n+=1
                except OSError:
                    pass
        return n
    print(
        "ACK_LIVE_DIAG"
        f"|runtime_version={version}"
        f"|ack_count={len(ack)}"
        f"|last_ack={last[-220:].replace('|','/')}"
        f"|recent_inflight={recent_count('inflight')}"
        f"|recent_sent={recent_count('sent')}",
        flush=True,
    )
    return 42

if __name__=="__main__":
    raise SystemExit(main())
