#!/usr/bin/env python3
import subprocess
from pathlib import Path
R=Path.home()/"prediction_research_prod"
p=subprocess.run(["git","status","--porcelain"],cwd=R,text=True,capture_output=True,timeout=30)
ps=[x[3:] for x in p.stdout.splitlines() if x.strip() and not x.startswith("??") and x[3:].startswith("control/tampermonkey_multichat/")]
if not ps: raise SystemExit(180)
groups=[("prediction-chat-wake.user.js",181),("prediction-nightshift-wake.user.js",182),("bridge_server_hardened.py",183),("bridge_server_v2.py",184),("command_router.py",185),("nightshift_server_heartbeat.py",186)]
for name,code in groups:
    if any(x.endswith(name) for x in ps): raise SystemExit(code)
if any("/patch_" in x for x in ps): raise SystemExit(187)
if any("/test_" in x for x in ps): raise SystemExit(188)
if any(x.endswith((".md",".json")) for x in ps): raise SystemExit(189)
raise SystemExit(190)
