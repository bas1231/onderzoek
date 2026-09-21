#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import subprocess

ROOT=Path.home()/"prediction_research_weather"
PY=Path.home()/"prediction_research/.venv/bin/python"
BRANCH="ai/weather-madis-ldm-a19b"
JOB=ROOT/"control/jobs/validate_kernel_clock_a19b_v2.py"

def run(*args,timeout=120):
    return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout)

def emit(obj,code=0):
    obj.update({"economic_conclusion":"NO_PROVEN_EDGE","live_trading":False,"paid_action":False,"wallet_action":False})
    print(json.dumps(obj,indent=2,sort_keys=True)); raise SystemExit(code)

if not ROOT.is_dir(): emit({"status":"BLOCKED","next_gate":"WEATHER_WORKTREE_MISSING"},2)
if not PY.is_file(): emit({"status":"BLOCKED","next_gate":"PREDICTION_VENV_PYTHON_MISSING"},3)
if run("git","branch","--show-current",timeout=20).stdout.strip()!=BRANCH:
    emit({"status":"BLOCKED","next_gate":"WRONG_WEATHER_BRANCH"},4)
if run("git","status","--porcelain","--untracked-files=no",timeout=20).stdout.strip():
    emit({"status":"BLOCKED","next_gate":"WEATHER_WORKTREE_TRACKED_CHANGES"},5)
pull=run("git","pull","--ff-only","origin",BRANCH,timeout=120)
if pull.returncode!=0:
    emit({"status":"BLOCKED","next_gate":"WEATHER_BRANCH_FAST_FORWARD_FAILED","stderr":pull.stderr[-3000:]},6)
if not JOB.is_file(): emit({"status":"BLOCKED","next_gate":"CLOCK_VALIDATOR_MISSING"},7)
cp=run(str(PY),str(JOB.relative_to(ROOT)),timeout=120)
try: obj=json.loads(cp.stdout)
except Exception: obj={}
emit({"status":"COMPLETED_CLOCK_GATE" if cp.returncode==0 else "BLOCKED_CLOCK_VALIDATION","validator":obj,"next_gate":obj.get("next_gate"),"weather_head":run("git","rev-parse","HEAD",timeout=20).stdout.strip()},0 if cp.returncode==0 else 8)
