from pathlib import Path
from datetime import datetime,timezone
import json
import subprocess

root=Path.cwd()
protocol_path=root/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json'
evaluator=root/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'
marker=Path.home()/'.local/state/prediction-research/analysis/kwi_full_station_checkpoints/KWI-FULL-STATION-PRECANONICAL-24H-V1-finalized.json'
if not protocol_path.exists():
    print('KWI_FULL_STATION_HOURLY_SKIP','protocol_missing')
    raise SystemExit(0)
if not evaluator.exists():
    print('KWI_FULL_STATION_HOURLY_SKIP','evaluator_missing')
    raise SystemExit(0)
protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
end=datetime.fromisoformat(str(protocol.get('window_end')))
now=datetime.now(timezone.utc)
if now>end and marker.exists():
    print('KWI_FULL_STATION_HOURLY_SKIP','finalized')
    raise SystemExit(0)
try:
    result=subprocess.run([str(root/'.venv/bin/python'),str(evaluator)],check=False,timeout=180,cwd=str(root))
except Exception as exc:
    print('KWI_FULL_STATION_HOURLY_ERROR',str(exc))
    raise SystemExit(0)
print('KWI_FULL_STATION_EVALUATOR_RC',result.returncode)
if result.returncode!=0:
    raise SystemExit(0)
if now>end:
    marker.parent.mkdir(parents=True,exist_ok=True)
    payload=dict(protocol_id=protocol.get('protocol_id'),window_end=end.isoformat(),finalized_at=datetime.now(timezone.utc).isoformat(),evaluator='control/jobs/evaluate_kwi_full_station_checkpoint_e369.py')
    marker.write_text(json.dumps(payload,indent=2,sort_keys=True)+chr(10),encoding='utf-8')
    print('KWI_FULL_STATION_FINAL_MARKER',marker)
print('KWI_FULL_STATION_HOURLY_PASS')
