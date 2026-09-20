from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess

root=Path.cwd()
protocol_path=root/'knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'
marker_path=root/'knowledge/raw/market_data/polymarket_fill_checkpoints/ASSET-RANK-MAKER-HEDGE-V1-24h-finalized.json'
if not protocol_path.exists():
    print('ASSET_FILL_HOURLY_SKIP','protocol_missing')
    raise SystemExit(0)
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
end_raw=str(protocol.get('window_end') or '')
if not end_raw:
    print('ASSET_FILL_HOURLY_SKIP','window_end_missing')
    raise SystemExit(0)
now=datetime.now(timezone.utc)
end=datetime.fromisoformat(end_raw)
if now>end and marker_path.exists():
    print('ASSET_FILL_HOURLY_SKIP','final_checkpoint_already_recorded')
    raise SystemExit(0)
cmd=[str(root/'.venv/bin/python'),str(root/'control/jobs/evaluate_asset_fill_checkpoint_e352.py')]
try:
    result=subprocess.run(cmd,check=False,timeout=180,cwd=str(root))
except Exception as exc:
    print('ASSET_FILL_HOURLY_ERROR',str(exc))
    raise SystemExit(0)
print('ASSET_FILL_HOURLY_EVALUATOR_RC',result.returncode)
if result.returncode!=0:
    raise SystemExit(0)
if now>end:
    marker_path.parent.mkdir(parents=True,exist_ok=True)
    marker=dict(protocol_id=protocol.get('protocol_id'),window_end=end.isoformat(),finalized_at=datetime.now(timezone.utc).isoformat(),evaluator='control/jobs/evaluate_asset_fill_checkpoint_e352.py')
    marker_path.write_text(json.dumps(marker,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
    print('ASSET_FILL_FINAL_MARKER',marker_path)
print('ASSET_FILL_HOURLY_PASS')
