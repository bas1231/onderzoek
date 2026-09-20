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
