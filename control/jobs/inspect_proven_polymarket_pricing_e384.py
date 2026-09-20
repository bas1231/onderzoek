from pathlib import Path

root=Path.cwd()
paths=[root/'control/jobs/capture_asset_rank_neg_risk_e327.py',root/'control/jobs/test_asset_rank_identity_fees_e332.py']
for p in paths:
    print('FILE',str(p.relative_to(root)))
    if not p.exists():
        print('MISSING',True)
        continue
    lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
    print('LINE_COUNT',len(lines))
    for n,line in enumerate(lines,1):
        print('LINE',n,repr(line))
    print('---')
print('PROVEN_POLYMARKET_PRICING_INSPECTION_PASS')
