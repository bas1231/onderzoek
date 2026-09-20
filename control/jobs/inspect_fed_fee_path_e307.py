from pathlib import Path

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_partial'
print('BASE_EXISTS',base.exists())
if base.exists():
    for p in sorted(base.iterdir()):
        print('FILE',p.name)
print('GLOB_COUNT',len(list(base.glob('*51456.json'))) if base.exists() else 0)
script=root/'control/jobs/kill_test_fed_fees_e306.py'
print('SCRIPT_EXISTS',script.exists())
if script.exists():
    lines=script.read_text(encoding='utf-8').splitlines()
    for n,line in enumerate(lines[:30],1):
        print('LINE',n,line)
