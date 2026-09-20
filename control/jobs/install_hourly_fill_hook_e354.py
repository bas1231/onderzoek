from pathlib import Path
import subprocess

root=Path.cwd()
q=chr(39)

evaluator=root/'control/jobs/evaluate_asset_fill_checkpoint_e352.py'
if not evaluator.exists():
    raise SystemExit('evaluator_missing')
text=evaluator.read_text(encoding='utf-8')
if 'upper_credit_epoch' not in text:
    anchor='credit_epoch=int(credit_dt.timestamp())+1'
    if text.count(anchor)!=1:
        raise SystemExit('credit_anchor_unexpected')
    extra=list()
    extra.append('protocol_path=root/'+q+'knowledge/candidates/protocols/ASSET-RANK-MAKER-HEDGE-V1-fill-feasibility-24h-v1.json'+q)
    extra.append('protocol=json.loads(protocol_path.read_text(encoding='+q+'utf-8'+q+'))')
    extra.append('window_end_dt=datetime.fromisoformat(str(protocol.get('+q+'window_end'+q+') or '+q+q+'))')
    extra.append('window_end_epoch=int(window_end_dt.timestamp())-1')
    extra.append('now_epoch=int(datetime.now(timezone.utc).timestamp())')
    extra.append('upper_credit_epoch=min(now_epoch,window_end_epoch)')
    text=text.replace(anchor,anchor+chr(10)+chr(10).join(extra),1)

    needle='    if ts<credit_epoch:'+chr(10)+'        continue'
    if text.count(needle)!=1:
        raise SystemExit('lower_bound_anchor_unexpected')
    replacement=needle+chr(10)+'    if ts>upper_credit_epoch:'+chr(10)+'        continue'
    text=text.replace(needle,replacement,1)

    lines=text.splitlines()
    out=list()
    inserted=False
    for line in lines:
        out.append(line)
        if line.startswith('result=dict(event_id='):
            out.append('result['+q+'window_end_effective_epoch'+q+']=window_end_epoch')
            out.append('result['+q+'upper_credit_epoch'+q+']=upper_credit_epoch')
            out.append('result['+q+'upper_credit_utc'+q+']=datetime.fromtimestamp(upper_credit_epoch,timezone.utc).isoformat()')
            out.append('result['+q+'final_window_checkpoint'+q+']=now_epoch>window_end_epoch')
            inserted=True
    if not inserted:
        raise SystemExit('result_anchor_missing')
    text=chr(10).join(out)+chr(10)
    compile(text,str(evaluator),'exec')
    evaluator.write_text(text,encoding='utf-8')
    print('EVALUATOR_WINDOW_BOUND_PATCHED')
else:
    print('EVALUATOR_WINDOW_BOUND_ALREADY_PRESENT')

cycle=root/'control/hourly/edge_hunter_cycle.py'
if not cycle.exists():
    raise SystemExit('edge_hunter_cycle_missing')
cycle_text=cycle.read_text(encoding='utf-8')
hook_name='hourly_asset_fill_checkpoint_e354.py'
if hook_name not in cycle_text:
    snippet=list()
    snippet.append('')
    snippet.append('import subprocess')
    snippet.append('try:')
    snippet.append('    checkpoint=subprocess.run([str(ROOT / '+q+'.venv/bin/python'+q+'),str(ROOT / '+q+'control/jobs/hourly_asset_fill_checkpoint_e354.py'+q+')],check=False,timeout=180,cwd=str(ROOT))')
    snippet.append('    print('+q+'ASSET_FILL_CHECKPOINT_RC'+q+',checkpoint.returncode)')
    snippet.append('except Exception as exc:')
    snippet.append('    print('+q+'ASSET_FILL_CHECKPOINT_ERROR'+q+',str(exc))')
    cycle_text=cycle_text.rstrip()+chr(10)+chr(10).join(snippet)+chr(10)
    compile(cycle_text,str(cycle),'exec')
    cycle.write_text(cycle_text,encoding='utf-8')
    print('HOURLY_EDGE_HUNTER_HOOK_PATCHED')
else:
    print('HOURLY_EDGE_HUNTER_HOOK_ALREADY_PRESENT')

helper=root/'control/jobs/hourly_asset_fill_checkpoint_e354.py'
compile(helper.read_text(encoding='utf-8'),str(helper),'exec')
result=subprocess.run([str(root/'.venv/bin/python'),str(helper)],check=False,timeout=180,cwd=str(root))
print('HOOK_SMOKE_RC',result.returncode)
if result.returncode!=0:
    raise SystemExit('hook_smoke_failed')
print('HOURLY_FILL_HOOK_INSTALL_PASS')
