from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT / "control/hourly/hourly_cycle.py"), run_name="__main__")
runs = sorted((ROOT / "knowledge/runs").glob("hourly-*.json"), key=lambda p: p.stat().st_mtime)
if not runs:
    raise SystemExit("no hourly run found")
run_id = runs[-1].stem
sys.path.insert(0, str(ROOT / "control/edge_hunter"))
from director import prepare
packet = prepare(run_id)
print("EDGE_HUNTER_PACKET", packet)

import subprocess
try:
    checkpoint=subprocess.run([str(ROOT / '.venv/bin/python'),str(ROOT / 'control/jobs/hourly_asset_fill_checkpoint_e354.py')],check=False,timeout=180,cwd=str(ROOT))
    print('ASSET_FILL_CHECKPOINT_RC',checkpoint.returncode)
except Exception as exc:
    print('ASSET_FILL_CHECKPOINT_ERROR',str(exc))

try:
    kwi_checkpoint=subprocess.run([str(ROOT / '.venv/bin/python'),str(ROOT / 'control/jobs/hourly_kwi_full_station_checkpoint_e371.py')],check=False,timeout=180,cwd=str(ROOT))
    print('KWI_FULL_STATION_CHECKPOINT_RC',kwi_checkpoint.returncode)
except Exception as exc:
    print('KWI_FULL_STATION_CHECKPOINT_ERROR',str(exc))

# AUTO_DURABLE_GIT_CHECKPOINT_V1
# Publish only durable research metadata after all hourly/KWI checkpoints.
try:
    checkpoint = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "control/hourly/git_checkpoint.py"),
        ],
        cwd=ROOT,
        check=False,
    )
    print("GIT_CHECKPOINT_RC", checkpoint.returncode)
except Exception as exc:
    # Research collection must continue even if Git publishing fails.
    # Publisher itself is fail-closed and never merges/rebases.
    print("GIT_CHECKPOINT_ERROR", str(exc))

