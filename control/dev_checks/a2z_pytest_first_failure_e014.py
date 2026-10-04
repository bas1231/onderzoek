from __future__ import annotations
import subprocess,re,sys
cmd=["/home/leonh/prediction_research_prod/.venv/bin/python","-m","pytest","-q","-x","tests/codex_supervisor"]
p=subprocess.run(cmd,cwd="/home/leonh/prediction_research_prod",text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
out=p.stdout or ""
if p.returncode==0:
    print("PYTEST_DIAG_PASS")
    raise SystemExit(0)
m=re.search(r"^FAILED\s+([^\n]+)$",out,re.M)
detail=(m.group(1) if m else "UNKNOWN_PYTEST_FAILURE")
detail=re.sub(r"\s+"," ",detail).strip()[:110]
print("ERROR_CLASS="+detail)
raise SystemExit(1)
