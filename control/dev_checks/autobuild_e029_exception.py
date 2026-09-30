from pathlib import Path
import os, shutil, subprocess

prod=Path.home()/"prediction_research_prod"
root=Path.cwd()

def gp(*args):
    cp=subprocess.run(["git",*args],cwd=prod,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if cp.returncode: raise SystemExit("PROD_GIT_FAIL="+(cp.stdout or "")[-500:])
    return [x.strip() for x in cp.stdout.splitlines() if x.strip()]

# Reproduce current local wiring context.
for rel in sorted(set(gp("ls-files","tests","control/codex_supervisor")) | set(gp("ls-files","--others","--exclude-standard","tests","control/codex_supervisor"))):
    src=prod/rel; dst=root/rel
    if src.is_file():
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)

# Apply exactly the E028 generic NEEDS_BUILD patch.
p=root/"control/codex_supervisor/candidate_dispatch.py"
s=p.read_text(encoding="utf-8")
old="    if state=='NEEDS_BUILD':\n        repo=P(task['candidate_source_root'])"
new="    if state=='NEEDS_BUILD' and protocols:\n        repo=P(task['candidate_source_root'])"
if old in s: p.write_text(s.replace(old,new,1),encoding="utf-8")
elif new not in s: raise SystemExit("PATCH_NOT_FOUND")

env=os.environ.copy(); env.pop("PYTEST_ADDOPTS",None)
log=root/"control/dev_checks/pytest_e029.log"
cp=subprocess.run([str(prod/".venv/bin/python"),"-m","pytest","-q","--tb=short",f"--log-file={log}","tests/codex_supervisor/test_autobuild_runtime_wiring_e004i.py"],cwd=root,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
out=cp.stdout or ""
if cp.returncode==0: raise SystemExit("WIRING_UNEXPECTED_PASS")
lines=[x.strip() for x in out.splitlines() if x.strip()]
# Preserve only the actual exception/assertion summary lines and final failure summary.
interesting=[x for x in lines if x.startswith("E   ") or "Error:" in x or "FAILED " in x or x.startswith("FAILED")]
if not interesting: interesting=lines[-8:]
raise SystemExit("WIRING_EXCEPTION="+" | ".join(interesting[-8:])[:3200])
