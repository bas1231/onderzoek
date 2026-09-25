#!/usr/bin/env python3
"""Test de bewaarde deploymentpayload in een geïsoleerde bronboom."""
import os, pathlib, shutil, subprocess, tempfile, json, datetime
ROOT=pathlib.Path(__file__).resolve().parents[3]
HERE=pathlib.Path(__file__).resolve().parent

def run(output, sockets=False):
    output=pathlib.Path(output);output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='runtime-reconcile-tests-') as tmp:
        tree=pathlib.Path(tmp)/'repo';tree.mkdir()
        for folder in ('control','tests','agents'):
            shutil.copytree(ROOT/folder,tree/folder,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
        p=tree/'knowledge/codex_audit/evidence';p.mkdir(parents=True)
        
        for name in ('test_audit_regressions.py','reproduce_defects.py','composer_reproduction.js'):
            shutil.copy2(ROOT/'knowledge/codex_audit/evidence'/name,p)
        for source in (HERE/'payload').rglob('*.py'):
            dest=tree/source.relative_to(HERE/'payload');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
        scopes=['tests/audit','knowledge/codex_audit/evidence/test_audit_regressions.py','control/weather','tests/hourly/test_agent_orchestrator.py','control/tampermonkey_multichat/test_install_hardened_bridge_fast_deadman_static.py']
        if sockets:
            p=tree/'knowledge/codex_audit/canonical';p.mkdir(parents=True)
            shutil.copy2(ROOT/'knowledge/codex_audit/canonical/test_external_runtime.py',p)
            scopes+=['control/tampermonkey_multichat/test_bridge_server_sent_semantics.py','knowledge/codex_audit/canonical/test_external_runtime.py']
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(tree)+':'+str(tree/'control/weather'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        cmd=[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*scopes,'--tb=short','-o','cache_dir='+tmp+'/cache']
        proc=subprocess.run(cmd,cwd=tree,env=env,capture_output=True,text=True,timeout=240)
        (output/'payload_tests.log').write_text(proc.stdout+proc.stderr)
        (output/'payload_tests.json').write_text(json.dumps({'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'exit_code':proc.returncode,'sockets':sockets,'scope':'Geïsoleerde bronboom met exact bewaarde deploymentpayload; geen productie-E2E'},indent=2)+'\n')
        return proc.returncode
if __name__=='__main__':raise SystemExit(run(HERE/'tests'))
