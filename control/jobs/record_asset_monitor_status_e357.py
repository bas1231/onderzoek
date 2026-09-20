from pathlib import Path
from datetime import datetime,timezone
import json

root=Path.cwd()
p=root/'knowledge/candidates/ASSET-RANK-MAKER-HEDGE-V1.json'
if not p.exists():
    raise SystemExit('candidate_missing')
data=json.loads(p.read_text(encoding='utf-8'))
old_phase=data.get('phase')
old_decision=data.get('decision')
status=dict()
status['status']='ACTIVE'
status['recorded_at']=datetime.now(timezone.utc).isoformat()
status['protocol']='knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'
status['baseline']='knowledge/raw/market_data/polymarket_shadow_baselines/20260920T022654Z106981_fill_baseline.json'
status['checkpoint_directory']='knowledge/raw/market_data/polymarket_fill_checkpoints'
status['scheduler_unit']='prediction-research-hourly-director.timer'
status['cadence']='hourly_on_the_hour'
status['timer_active']=True
status['timer_enabled']=True
status['persistent']=True
status['randomized_delay_seconds']=0
status['verified_next_trigger_local']='2026-09-20T05:00:00+02:00'
status['fill_credit_rule']='taker SELL executions on exact YES maker bid only'
status['cancellation_fill_credit']=False
status['partial_fill_credit']=False
status['current_full_shadow_fill_count']=0
status['scientific_interpretation']='prospective execution feasibility monitoring active; no edge proven'
data['prospective_monitoring']=status
if data.get('phase')!=old_phase or data.get('decision')!=old_decision:
    raise SystemExit('phase_or_decision_changed_unexpectedly')
p.write_text(json.dumps(data,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
print('CANDIDATE_ID',data.get('candidate_id'))
print('PHASE',data.get('phase'))
print('DECISION',data.get('decision'))
print('MONITOR_STATUS',status.get('status'))
print('CADENCE',status.get('cadence'))
print('CURRENT_FULL_SHADOW_FILL_COUNT',status.get('current_full_shadow_fill_count'))
print('NEXT_VERIFIED_TRIGGER_LOCAL',status.get('verified_next_trigger_local'))
print('ASSET_MONITOR_STATUS_RECORD_PASS')
