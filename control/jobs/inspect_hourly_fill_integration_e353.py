from pathlib import Path

root=Path.cwd()
paths=[
    root/'control/hourly/edge_hunter_cycle.py',
    root/'control/hourly/hourly_cycle.py',
    root/'control/jobs/evaluate_asset_fill_checkpoint_e352.py'
]
for p in paths:
    print('FILE',str(p.relative_to(root)),'EXISTS',p.exists())
    if not p.exists():
        continue
    lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
    print('LINE_COUNT',len(lines))
    start=max(1,len(lines)-80)
    for n in range(start,len(lines)+1):
        line=lines[n-1]
        print('LINE',n,repr(line))
    print('---')

for base in [root/'control',root/'docs']:
    if not base.exists():
        continue
    hits=list()
    for p in base.rglob('*'):
        if not p.is_file():
            continue
        try:
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        if 'edge_hunter_cycle.py' in low or 'hourly-director' in low or 'systemd' in low and 'hourly' in low:
            hits.append(str(p.relative_to(root)))
    for item in sorted(set(hits))[:80]:
        print('INTEGRATION_HIT',item)
print('HOURLY_FILL_INTEGRATION_INSPECTION_PASS')
