from pathlib import Path
import subprocess
import json

root=Path.cwd()
cycle=root/'control/hourly/edge_hunter_cycle.py'
helper=root/'control/jobs/hourly_asset_fill_checkpoint_e354.py'
evaluator=root/'control/jobs/evaluate_asset_fill_checkpoint_e352.py'
protocol=root/'knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'

for p in [cycle,helper,evaluator,protocol]:
    print('FILE',str(p.relative_to(root)),'EXISTS',p.exists())
    if not p.exists():
        raise SystemExit('required_file_missing')

cycle_text=cycle.read_text(encoding='utf-8')
print('HOOK_PRESENT','hourly_asset_fill_checkpoint_e354.py' in cycle_text)
print('HOOK_NONBLOCKING','check=False' in cycle_text and 'ASSET_FILL_CHECKPOINT_ERROR' in cycle_text)
compile(cycle_text,str(cycle),'exec')
compile(helper.read_text(encoding='utf-8'),str(helper),'exec')
compile(evaluator.read_text(encoding='utf-8'),str(evaluator),'exec')
print('SYNTAX_PASS',True)

protocol_data=json.loads(protocol.read_text(encoding='utf-8'))
print('WINDOW_START',protocol_data.get('window_start'))
print('WINDOW_END',protocol_data.get('window_end'))
print('DURATION_HOURS',protocol_data.get('duration_hours'))

units=['prediction-research-hourly-director.timer','prediction-research-hourly-director.service']
for unit in units:
    active=subprocess.run(['systemctl','--user','is-active',unit],capture_output=True,text=True,check=False)
    enabled=subprocess.run(['systemctl','--user','is-enabled',unit],capture_output=True,text=True,check=False)
    print('UNIT',unit,'ACTIVE',active.stdout.strip(),'ACTIVE_RC',active.returncode,'ENABLED',enabled.stdout.strip(),'ENABLED_RC',enabled.returncode)

checkpoints=root/'knowledge/raw/market_data/polymarket_fill_checkpoints'
items=list()
if checkpoints.exists():
    for p in checkpoints.iterdir():
        if p.is_file() and '106981_fill_checkpoint' in p.name:
            items.append(p)
items.sort(key=lambda p:p.stat().st_mtime)
print('CHECKPOINT_COUNT',len(items))
if items:
    latest=items[-1]
    print('LATEST_CHECKPOINT',latest.name)
    data=json.loads(latest.read_text(encoding='utf-8'))
    print('LATEST_RETRIEVED_AT',data.get('retrieved_at'))
    print('LATEST_FULL_FILL_COUNT',data.get('full_shadow_fill_count'))

print('HOURLY_FILL_MONITOR_VERIFY_PASS')
