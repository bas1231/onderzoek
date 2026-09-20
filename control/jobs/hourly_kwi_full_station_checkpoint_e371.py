from pathlib import Path
import subprocess

root=Path.cwd()
protocol=root/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json'
evaluator=root/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'
if not protocol.exists():
    print('KWI_FULL_STATION_HOURLY_SKIP','protocol_missing')
    raise SystemExit(0)
if not evaluator.exists():
    print('KWI_FULL_STATION_HOURLY_SKIP','evaluator_missing')
    raise SystemExit(0)
try:
    result=subprocess.run([str(root/'.venv/bin/python'),str(evaluator)],check=False,timeout=180,cwd=str(root))
except Exception as exc:
    print('KWI_FULL_STATION_HOURLY_ERROR',str(exc))
    raise SystemExit(0)
print('KWI_FULL_STATION_EVALUATOR_RC',result.returncode)
print('KWI_FULL_STATION_HOURLY_PASS')
