from pathlib import Path
import py_compile
import subprocess

root = Path.cwd()
p = root / 'control/jobs/scan_neg_risk_identities_e292.py'
t = p.read_text(encoding='utf-8')
old = 'type(exc).name'
new = 'type(exc).name'
if old not in t:
    raise SystemExit('broken_pattern_not_found')
t = t.replace(old,new)
p.write_text(t,encoding='utf-8')
py_compile.compile(str(p),doraise=True)
r = subprocess.run([str(root / '.venv/bin/python'),str(p.relative_to(root))],cwd=root)
if r.returncode:
    raise SystemExit(r.returncode)
print('NEG_RISK_SCAN_REPAIRED_AND_RERUN_PASS')
