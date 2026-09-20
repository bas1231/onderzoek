from pathlib import Path

root=Path.cwd()
p=root/'control/jobs/neg_risk_manifest_e296.py'
if not p.exists():
    raise SystemExit('scanner_missing')
lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
print('LINE_COUNT',len(lines))
for n,line in enumerate(lines,1):
    print('LINE',n,repr(line))
print('NEG_RISK_MANIFEST_SOURCE_INSPECTION_PASS')
