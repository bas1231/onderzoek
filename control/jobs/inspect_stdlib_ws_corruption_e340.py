from pathlib import Path

root=Path.cwd()
p=root/'control/jobs/smoke_asset_stdlib_ws_e339.py'
print('SCRIPT_EXISTS',p.exists())
if not p.exists():
    raise SystemExit('script_missing')
lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
print('LINE_COUNT',len(lines))
for n,line in enumerate(lines,1):
    if n>=68 and n<=95:
        print('LINE',n,repr(line))
print('STDLIB_WS_CORRUPTION_INSPECTION_PASS')
