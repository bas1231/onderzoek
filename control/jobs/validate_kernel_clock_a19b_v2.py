#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import py_compile
import subprocess
import sys

ROOT=Path.cwd()
W=ROOT/'control/weather'
PY=W/'kernel_clock_evidence_a19b_v2.py'
UNIT=W/'test_kernel_clock_evidence_a19b_v2.py'
ADV=W/'test_kernel_clock_evidence_a19b_v2_adversarial.py'
PROBE=ROOT/'control/jobs/probe_kernel_clock_a19b_v2.py'
sys.path.insert(0,str(W))
from kernel_clock_evidence_a19b_v2 import evaluate_kernel_clock_samples


def run(*args,timeout=60):
    return subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout)

result={"task":"WX-A19B-V2-KERNEL-CLOCK-THREE-CHECK","economic_conclusion":"NO_PROVEN_EDGE","live_trading":False,"paid_action":False,"wallet_action":False,"checks":{}}

try:
    for p in (PY,UNIT,ADV,PROBE): py_compile.compile(str(p),doraise=True)
    u=run(sys.executable,str(UNIT))
    c1=u.returncode==0 and 'A19B_KERNEL_CLOCK_EVIDENCE_UNIT_TESTS_PASS' in u.stdout
    result['checks']['check_1_technical']={"pass":c1,"stdout":u.stdout.strip(),"stderr":u.stderr[-2000:]}
except Exception as exc:
    c1=False; result['checks']['check_1_technical']={"pass":False,"detail":f"{type(exc).__name__}: {exc}"}

if c1:
    a=run(sys.executable,str(ADV))
    c2=a.returncode==0 and 'A19B_KERNEL_CLOCK_EVIDENCE_ADVERSARIAL_TESTS_PASS' in a.stdout
    result['checks']['check_2_fail_closed']={"pass":c2,"stdout":a.stdout.strip(),"stderr":a.stderr[-2000:]}
else:
    c2=False; result['checks']['check_2_fail_closed']={"pass":False,"status":"SKIPPED_CHECK_1_FAILED"}

if c1 and c2:
    p=run(sys.executable,str(PROBE),timeout=30)
    try: pobj=json.loads(p.stdout)
    except Exception: pobj={}
    samples=[]
    for row in pobj.get('samples') or []:
        probe=row.get('probe') if isinstance(row,dict) else None
        if isinstance(probe,dict): samples.append(probe)
    decision=evaluate_kernel_clock_samples(samples)
    c3=bool(p.returncode==0 and pobj.get('status')=='PROBE_COMPLETE' and len(samples)==5)
    result['checks']['check_3_real_kernel_probe']={"pass":c3,"probe_status":pobj.get('status'),"probe":pobj,"decision":decision,"stderr":p.stderr[-2000:]}
else:
    c3=False; decision={"evidence_clock_eligible":False,"decision":"CLOCK_EVIDENCE_BLOCKED","reasons":["EARLIER_CHECK_FAILED"]}
    result['checks']['check_3_real_kernel_probe']={"pass":False,"status":"SKIPPED_EARLIER_CHECK_FAILED"}

local_pass=bool(c1 and c2 and c3)
result['status']='PASS_LOCAL_BUILD' if local_pass else 'BLOCKED_LOCAL_VALIDATION'
result['clock_evidence']=decision
if not local_pass:
    result['next_gate']='FIX_KERNEL_CLOCK_VALIDATION'
elif decision.get('evidence_clock_eligible') is True:
    result['next_gate']='BLOCKED_NOAA_MADIS_LDM_ACCESS_OR_RUNTIME'
else:
    result['next_gate']='BLOCKED_CLOCK_EVIDENCE'
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(0 if local_pass else 1)
