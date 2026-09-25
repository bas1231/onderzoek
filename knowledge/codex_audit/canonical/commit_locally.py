#!/usr/bin/env python3
"""Maak uitsluitend lokale repaircommits; laat overige staged ownerwerk staan.

LET OP: de routercommit bevat ook de vooraf staged consumer-routingbasis in
command_router.py. Deze basis is exact geverifieerd en blijft inhoudelijk behouden.
Er wordt geen ander staged ownerbestand meegenomen. Geen push of hooks toegestaan.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.STDOUT)

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    if os.environ.get('GIT_INDEX_FILE') or os.environ.get('GIT_DIR'):
        raise RuntimeError('STOP: afwijkende Git-omgeving; eerst handmatig beoordelen.')
    if Path(git('rev-parse','--show-toplevel').decode().strip()).resolve()!=ROOT:
        raise RuntimeError('STOP: verkeerde repository.')
    manifest=json.loads((HERE/'canonical_change_manifest.json').read_text())
    pre=json.loads((HERE/'preflight.json').read_text())
    if git('rev-parse','HEAD').decode().strip()!=manifest['source_commit']:
        raise RuntimeError('STOP: HEAD gewijzigd; commitplan opnieuw afstemmen, niets overschreven.')
    if digest(git('diff','--cached','--binary'))!=pre['index_diff_sha256']:
        raise RuntimeError('STOP: ownerindex gewijzigd; commitplan opnieuw afstemmen.')
    for row in manifest['paths']:
        if digest((ROOT/row['path']).read_bytes())!=row['canonical_sha256']:
            raise RuntimeError('STOP: canonical bron gewijzigd: '+row['path'])
    hookpath=Path(git('rev-parse','--git-path','hooks').decode().strip())
    if not hookpath.is_absolute():hookpath=ROOT/hookpath
    if hookpath.exists() and any(p.is_file() and not p.name.endswith('.sample') and os.access(p,os.X_OK) for p in hookpath.iterdir()):
        raise RuntimeError('STOP: actieve Git-hooks vereisen review; script omzeilt geen hooks.')
    paths=[x['path'] for x in manifest['paths'] if not x['path'].startswith('knowledge/')]
    testpaths=[p for p in paths if p.startswith('tests/') or '/test_' in p]
    groups=[('test: preserve canonical audit regression contracts',testpaths),
            ('fix: enforce weather receipt and prospective target validity',[p for p in paths if p not in testpaths and (p.startswith('control/weather/') or p.startswith('control/jobs/'))]),
            ('fix: reject invalid economics in proof gate',['control/hourly/agent_orchestrator.py']),
            ('fix: restore executor policy and terminal failure handling',['control/executor.py','control/policy_check.py','control/policy.json']),
            ('fix: reconcile consumer routing and verified browser delivery',['control/tampermonkey_multichat/command_router.py','control/tampermonkey_multichat/prediction-chat-wake.user.js']),
            ('audit: qualify canonical repairs and remaining blockers',['knowledge/codex_audit'])]
    excluded=[':(exclude)'+p for p in paths]+[':(exclude)knowledge/codex_audit']
    protected=digest(git('diff','--cached','--binary','--','.',*excluded))
    print('Routercommit omvat de bewaarde staged consumer-routingbasis plus auditreparaties.')
    for message,selected in groups:
        if not selected:continue
        git('add','--',*selected)
        git('commit','--only','-m',message,'--',*selected)
        if digest(git('diff','--cached','--binary','--','.',*excluded))!=protected:
            raise RuntimeError('STOP: onverwachte wijziging in overige staged bestanden; niets automatisch herstellen.')
        print(git('rev-parse','--short','HEAD').decode().strip(),message)
    print('Lokale commits voltooid; overige staged ownerbestanden behouden; NIETS gepusht.')

if __name__=='__main__':
    try:main()
    except (RuntimeError,subprocess.CalledProcessError) as exc:
        print(str(exc) if isinstance(exc,RuntimeError) else 'STOP: Git-opdracht mislukt; geen push/reset/cleanup uitgevoerd.',file=sys.stderr)
        raise SystemExit(1)
