from pathlib import Path
import subprocess

root=Path.cwd()
cycle=root/'control/hourly/edge_hunter_cycle.py'
helper=root/'control/jobs/hourly_kwi_full_station_checkpoint_e371.py'
evaluator=root/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'
protocol=root/'knowledge/candidates/protocols/KWI-FULL-STATION-PRECANONICAL-24H-V1.json'

for p in [cycle,helper,evaluator,protocol]:
    print('FILE',str(p.relative_to(root)),'EXISTS',p.exists())
    if not p.exists():
        raise SystemExit('required_file_missing')

cycle_text=cycle.read_text(encoding='utf-8')
helper_text=helper.read_text(encoding='utf-8')
compile(cycle_text,str(cycle),'exec')
compile(helper_text,str(helper),'exec')
compile(evaluator.read_text(encoding='utf-8'),str(evaluator),'exec')

print('HOOK_PRESENT','hourly_kwi_full_station_checkpoint_e371.py' in cycle_text)
print('HOOK_NONBLOCKING','check=False' in cycle_text and 'KWI_FULL_STATION_CHECKPOINT_ERROR' in cycle_text)
print('FINALIZATION_GUARD_PRESENT','finalized' in helper_text and 'window_end' in helper_text)

result=subprocess.run([str(root/'.venv/bin/python'),str(helper)],check=False,timeout=180,cwd=str(root),capture_output=True,text=True)
print('HELPER_RC',result.returncode)
print('HELPER_STDOUT_BEGIN')
print(result.stdout[:12000])
print('HELPER_STDOUT_END')
if result.stderr.strip():
    print('HELPER_STDERR',result.stderr[:4000])
if result.returncode!=0:
    raise SystemExit('helper_smoke_failed')

print('KWI_HOURLY_MONITOR_VERIFY_PASS')
