from pathlib import Path
import subprocess

root=Path.cwd()
cycle=root/'control/hourly/edge_hunter_cycle.py'
helper=root/'control/jobs/hourly_kwi_full_station_checkpoint_e371.py'
evaluator=root/'control/jobs/evaluate_kwi_full_station_checkpoint_e369.py'
for p in [cycle,helper,evaluator]:
    if not p.exists():
        raise SystemExit('required_file_missing')
compile(helper.read_text(encoding='utf-8'),str(helper),'exec')
compile(evaluator.read_text(encoding='utf-8'),str(evaluator),'exec')
text=cycle.read_text(encoding='utf-8')
hook='hourly_kwi_full_station_checkpoint_e371.py'
if hook not in text:
    q=chr(39)
    lines=list()
    lines.append('')
    lines.append('try:')
    lines.append('    kwi_checkpoint=subprocess.run([str(ROOT / '+q+'.venv/bin/python'+q+'),str(ROOT / '+q+'control/jobs/hourly_kwi_full_station_checkpoint_e371.py'+q+')],check=False,timeout=180,cwd=str(ROOT))')
    lines.append('    print('+q+'KWI_FULL_STATION_CHECKPOINT_RC'+q+',kwi_checkpoint.returncode)')
    lines.append('except Exception as exc:')
    lines.append('    print('+q+'KWI_FULL_STATION_CHECKPOINT_ERROR'+q+',str(exc))')
    text=text.rstrip()+chr(10)+chr(10).join(lines)+chr(10)
    compile(text,str(cycle),'exec')
    cycle.write_text(text,encoding='utf-8')
    print('KWI_HOURLY_HOOK_PATCHED')
else:
    print('KWI_HOURLY_HOOK_ALREADY_PRESENT')
result=subprocess.run([str(root/'.venv/bin/python'),str(helper)],check=False,timeout=180,cwd=str(root))
print('KWI_HOOK_SMOKE_RC',result.returncode)
if result.returncode!=0:
    raise SystemExit('kwi_hook_smoke_failed')
print('KWI_HOURLY_HOOK_INSTALL_PASS')
