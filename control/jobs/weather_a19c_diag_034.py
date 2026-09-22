#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import shutil
import subprocess

MAIN=Path.home()/"prediction_research"
WX=Path.home()/"prediction_research_weather"
TASK="WEATHER-A19C-CLOCK-GATE-034"
KEYS=("a19c","clock","chrony","ntp","uncertainty","offset","ldm")

def run(cmd,cwd=None,timeout=20):
    try:
        cp=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
        return {"returncode":cp.returncode,"stdout":cp.stdout[-16000:],"stderr":cp.stderr[-8000:]}
    except Exception as exc:
        return {"error":f"{type(exc).__name__}: {exc}"}

def text(path,limit=30000):
    try:
        return path.read_text(encoding="utf-8",errors="replace")[-limit:] if path.is_file() else None
    except Exception as exc:
        return f"READ_ERROR {type(exc).__name__}: {exc}"

def collect(root,max_items=100):
    out=[]
    if not root.is_dir(): return out
    for p in root.rglob("*"):
        if not p.is_file(): continue
        low=p.as_posix().lower()
        if TASK.lower() in low or any(k in low for k in KEYS):
            try: out.append((p.stat().st_mtime_ns,p))
            except OSError: pass
    out.sort(reverse=True,key=lambda x:x[0])
    return [p for _,p in out[:max_items]]

out={"task":"WX-A19C-CLOCK-DIAG-035","target":TASK,"economic_conclusion":"NO_PROVEN_EDGE","live_trading":False,"paid_action":False,"wallet_action":False,"mutations":"NONE_READ_ONLY"}
if MAIN.is_dir():
    out["main_git"]={"head":run(["git","rev-parse","HEAD"],MAIN),"branch":run(["git","branch","--show-current"],MAIN)}
if WX.is_dir():
    out["weather_git"]={"head":run(["git","rev-parse","HEAD"],WX),"branch":run(["git","branch","--show-current"],WX),"status":run(["git","status","--porcelain"],WX),"log":run(["git","log","-15","--oneline","--decorate"],WX)}
paths=[]
for root in (MAIN/"control",WX/"control",WX/"evidence"/"weather"):
    paths.extend(collect(root))
seen=set(); items=[]
for p in paths:
    s=str(p)
    if s in seen: continue
    seen.add(s)
    item={"path":s,"size":p.stat().st_size}
    if p.suffix.lower() in {".json",".txt",".py",".md"} and p.stat().st_size<=250000:
        item["content"]=text(p,30000)
    items.append(item)
    if len(items)>=35: break
out["artifacts"]=items
clock={"chronyc_path":shutil.which("chronyc"),"timedatectl_path":shutil.which("timedatectl")}
if clock["chronyc_path"]: clock["chronyc_tracking"]=run([clock["chronyc_path"],"tracking","-n"])
if clock["timedatectl_path"]:
    clock["ntp_synchronized"]=run([clock["timedatectl_path"],"show","-p","NTPSynchronized","--value"])
    clock["timesync_status"]=run([clock["timedatectl_path"],"timesync-status"])
out["clock_inventory"]=clock
print(json.dumps(out,indent=2,sort_keys=True))
