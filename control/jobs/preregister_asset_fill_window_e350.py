from pathlib import Path
from datetime import datetime,timezone,timedelta
import json

root=Path.cwd()
candidate_path=root/'knowledge/candidates/ASSET-RANK-MAKER-HEDGE-V1.json'
if not candidate_path.exists():
    raise SystemExit('candidate_missing')

candidate=json.loads(candidate_path.read_text(encoding='utf-8'))
now=datetime.now(timezone.utc)
end=now+timedelta(hours=24)
protocol=dict()
protocol['protocol_id']='ASSET-RANK-MAKER-HEDGE-V1-FILL-FEASIBILITY-24H-V1'
protocol['created_at']=now.isoformat()
protocol['window_start']=now.isoformat()
protocol['window_end']=end.isoformat()
protocol['duration_hours']=24
protocol['event_id']='106981'
protocol['shadow_order_size']=5.0
protocol['maker_side']='YES'
protocol['maker_price_rule']='best bid observed at episode start for each YES leg'
protocol['queue_rule']='join behind full displayed quantity at that exact best bid'
protocol['cancellation_fill_credit']=False
protocol['trade_source']='Polymarket Data API v2 trades with taker_only true semantics'
protocol['qualifying_trade_rule']='only taker SELL executions on the same YES token at the exact shadow bid consume queue ahead'
protocol['full_fill_rule']='cumulative qualifying executed size must be at least initial queue ahead plus shadow order size'
protocol['partial_fill_credit']=False
protocol['pre_window_trade_credit']=False
protocol['book_change_fill_credit']=False
protocol['price_change_fill_credit']=False
protocol['last_trade_price_snapshot_fill_credit']=False
protocol['unknown_data_rule']='fail closed and do not credit a fill'
protocol['purpose']='prospective maker fill feasibility only; not PnL validation'
protocol['promotion_rule']='no promotion to execution edge from this test alone'
protocol['rejection_rule']='zero fills is negative evidence but not automatic rejection unless a separately preregistered materiality gate exists'
protocol['evidence_before_window']='discovery or historical feasibility only'

outdir=root/'knowledge/candidates/protocols'
outdir.mkdir(parents=True,exist_ok=True)
out=outdir/'ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'
out.write_text(json.dumps(protocol,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

refs=candidate.get('prospective_protocols')
if not isinstance(refs,list):
    refs=list()
ref=str(out.relative_to(root))
if ref not in refs:
    refs.append(ref)
candidate['prospective_protocols']=refs
candidate_path.write_text(json.dumps(candidate,indent=2,sort_keys=True)+chr(10),encoding='utf-8')

print('PROTOCOL_ID',protocol.get('protocol_id'))
print('WINDOW_START',protocol.get('window_start'))
print('WINDOW_END',protocol.get('window_end'))
print('DURATION_HOURS',protocol.get('duration_hours'))
print('CANCELLATION_FILL_CREDIT',protocol.get('cancellation_fill_credit'))
print('PARTIAL_FILL_CREDIT',protocol.get('partial_fill_credit'))
print('PATH',out)
print('CANDIDATE',candidate_path)
print('ASSET_FILL_WINDOW_PREREG_PASS')
