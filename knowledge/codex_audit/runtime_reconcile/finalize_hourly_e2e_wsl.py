#!/usr/bin/env python3
"""Fail-closed bereikbaarheidskwalificatie. Nooit een gesimuleerde E2E-PASS."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import uuid
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ALLOWED_GIT={('branch','--show-current'),('diff','--cached','--name-only','--')}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root,manifest):
    for name,digest in manifest.items():
        if sha(root/name)!=digest:raise RuntimeError('PROVENANCE_DIVERGED: '+name)

def readonly_git(*args):
    if args not in ALLOWED_GIT:raise RuntimeError('QUALIFICATION_FORBIDS_GIT_OPERATION: '+str(args[0] if args else 'empty'))
    env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_OPTIONAL_LOCKS':'0','GIT_ALLOW_PROTOCOL':''}
    return subprocess.run(['/usr/bin/git','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null',*args],cwd=ROOT,env=env,text=True,capture_output=True,timeout=15)

def assess(module):
    # De originele sync-guard blijft intact. Alleen IO begrensd; geen READY simuleren.
    module.git=readonly_git
    module.write_status=lambda status,**fields:dict(status=status,**fields)
    result=module.safe_sync()
    if result.get('status')=='READY':
        raise RuntimeError('UNEXPECTED_READY: geen autorisatie voor pushende downstreamketen')
    return result

def main():
    manifest=json.loads((HERE/'hourly_qualification_provenance.json').read_text())
    out=HERE/'hourly_final_runs'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
    result={'software_status':'AUDIT_INCOMPLETE','scientific_status':'NO_PROVEN_EDGE','scope':'Originele preflightguard met read-only Gitadapter; downstream niet uitgevoerd','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        verify(ROOT,manifest)
        preserve=json.loads((HERE/'preservation_manifest.json').read_text())
        before={p:sha(ROOT/p) for p in preserve['owner_work']};index=sha(ROOT/'.git/index')
        spec=importlib.util.spec_from_file_location('qualification_runtime_sync',ROOT/'control/hourly/runtime_sync.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        result['preflight']=assess(mod)
        result['owner_preserved']=before=={p:sha(ROOT/p) for p in before} and index==sha(ROOT/'.git/index')
        if not result['owner_preserved']:raise RuntimeError('OWNER_STATE_CHANGED_DURING_QUALIFICATION')
        result['blocker']=result['preflight'].get('error','PREFLIGHT_NOT_READY')
        result['downstream_blocker']='Originele verplichte Gitcheckpoint kan pushen. Omleiding/mock/skip bewijst geen volledige echte keten; geen downstream gestart.'
    except Exception as exc:
        result['blocker']=str(exc)[:1000];result['error_type']=type(exc).__name__
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    text='\n\n## Laatste hourly-bereikbaarheidskwalificatie\n\n**AUDIT_INCOMPLETE + RESIDUAL_RISK**. Bewijs: `'+str((out/'RESULT.json').relative_to(HERE.parent))+'`. Blokkade: '+result['blocker']+'. Geen productie-E2E uitgevoerd of PASS gesimuleerd. Oorspronkelijke guards behouden; geen push/handel/API. NO_PROVEN_EDGE afzonderlijk.\n'
    for name in ['FINAL_AUDIT_REPORT.md','OPEN_FINDINGS.md','TEST_MATRIX.md','REMEDIATION_LOG.md','RESIDUAL_RISKS.md']:
        with (HERE.parent/name).open('a') as f:f.write(text)
    print('BLOCKED:',result['blocker']);print(result.get('downstream_blocker',''));print('Bewijs:',out)
    return 2
if __name__=='__main__':raise SystemExit(main())
