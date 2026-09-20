from pathlib import Path

root=Path.cwd()
base=root/'knowledge/raw/market_rules/polymarket'
print('BASE_EXISTS',base.exists())
if base.exists():
    for p in sorted(base.glob('51456')):
        print('RULE_FILE',p.name)
script=root/'control/jobs/compute_fed_net_e310.py'
print('SCRIPT_EXISTS',script.exists())
if script.exists():
    for n,line in enumerate(script.read_text(encoding='utf-8').splitlines()[:20],1):
        print('LINE',n,line)
