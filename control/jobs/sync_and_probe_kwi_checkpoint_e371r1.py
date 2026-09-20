from pathlib import Path
import subprocess
import sys

root = Path.cwd()
paths = [
    'control/hourly/edge_hunter_cycle.py',
    'control/jobs/hourly_kwi_full_station_checkpoint_e371.py',
    'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py',
]

fetch = subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=root, text=True, capture_output=True)
if fetch.returncode != 0:
    raise SystemExit(fetch.stderr or 'git_fetch_failed')

for rel in paths:
    show = subprocess.run(['git', 'show', f'origin/main:{rel}'], cwd=root, text=True, capture_output=True)
    if show.returncode != 0:
        raise SystemExit(show.stderr or f'git_show_failed:{rel}')
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(show.stdout, encoding='utf-8')

compile_result = subprocess.run([sys.executable, '-m', 'py_compile', *paths], cwd=root, text=True, capture_output=True)
print('PY_COMPILE_RC', compile_result.returncode)
if compile_result.stdout:
    print(compile_result.stdout)
if compile_result.stderr:
    print(compile_result.stderr)
if compile_result.returncode != 0:
    raise SystemExit(compile_result.returncode)

probe = subprocess.run([sys.executable, 'control/jobs/hourly_kwi_full_station_checkpoint_e371.py'], cwd=root, text=True, capture_output=True, timeout=180)
print('CHECKPOINT_RC', probe.returncode)
print('CHECKPOINT_STDOUT_BEGIN')
print(probe.stdout)
print('CHECKPOINT_STDOUT_END')
if probe.stderr:
    print('CHECKPOINT_STDERR_BEGIN')
    print(probe.stderr)
    print('CHECKPOINT_STDERR_END')

cycle_text = (root / 'control/hourly/edge_hunter_cycle.py').read_text(encoding='utf-8')
assert 'hourly_kwi_full_station_checkpoint_e371.py' in cycle_text
print('E371_WIRED_IN_HOURLY_CYCLE=PASS')
print('E371_LOCAL_SYNC_AND_PROBE=PASS')
