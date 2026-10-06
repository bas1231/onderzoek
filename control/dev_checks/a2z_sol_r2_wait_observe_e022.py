import time
from pathlib import Path
ROOT=Path.home()/'.local/share/prediction-project-executor/campaigns/FULL-A2Z-LIVE-20261004-V4'
RESULT=ROOT/'model_results'/'A2Z-V4-SOL-PROPOSAL-20261006-R2.json'
time.sleep(600)
print('SOL_R2_OBSERVER_AFTER_WAIT=1 RESULT_PRESENT='+('1' if RESULT.is_file() and not RESULT.is_symlink() else '0')+' NO_MODEL_RESUME=1')
raise SystemExit(10)
