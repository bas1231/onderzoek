from pathlib import Path
from datetime import datetime, timedelta, timezone
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CADENCE = ROOT / 'control/hourly/work_cadence.py'
BRIDGE = ROOT / 'control/browser_bridge.py'
EXECUTOR = ROOT / 'control/executor.py'

spec = importlib.util.spec_from_file_location('cadence_test_module', CADENCE)
if spec is None or spec.loader is None:
    raise RuntimeError('cannot load cadence module')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

t0 = datetime(2026, 9, 20, 20, 0, tzinfo=timezone.utc)
with tempfile.TemporaryDirectory() as tmp:
    state = Path(tmp) / 'cadence.json'
    a = mod.check(now=t0, state_path=state, reason='test')
    assert a['allowed'] is True and a['mode'] == 'WORK'
    b = mod.check(now=t0 + timedelta(hours=3, minutes=59, seconds=59), state_path=state)
    assert b['allowed'] is True and b['mode'] == 'WORK'
    c = mod.check(now=t0 + timedelta(hours=4), state_path=state)
    assert c['allowed'] is False and c['mode'] == 'COOLDOWN'
    d = mod.check(now=t0 + timedelta(hours=4, minutes=59, seconds=59), state_path=state)
    assert d['allowed'] is False and d['mode'] == 'COOLDOWN'
    e = mod.check(now=t0 + timedelta(hours=5), state_path=state, start_if_idle=False, mutate=False)
    assert e['allowed'] is True and e['mode'] == 'IDLE'
    f = mod.check(now=t0 + timedelta(hours=5), state_path=state)
    assert f['allowed'] is True and f['mode'] == 'WORK'

with tempfile.TemporaryDirectory() as tmp:
    state = Path(tmp) / 'cadence.json'
    state.write_text('{broken', encoding='utf-8')
    bad = mod.check(now=t0, state_path=state)
    assert bad['allowed'] is False and bad['mode'] == 'ERROR'

bridge = BRIDGE.read_text(encoding='utf-8')
executor = EXECUTOR.read_text(encoding='utf-8')
assert 'WORK_CADENCE = load_work_cadence()' in bridge
assert "reason=f'bridge_task:{task.task_id}'" in bridge
assert 'work cadence blocked' in bridge
assert 'WORK_CADENCE = load_work_cadence()' in executor
assert "reason=f'executor_task:{task.task_id}'" in executor
assert 'executor blocked by work cadence' in executor
print('WORK_CADENCE_ENFORCEMENT_PASS')
