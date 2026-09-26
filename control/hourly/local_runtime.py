"""Expliciete remoteloze checkpointcapability voor een geïsoleerde hourlyrun."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

MODE='qualification_local'

def execution_mode():
    mode=os.environ.get('PREDICTION_EXECUTION_MODE','production')
    if mode not in ('production',MODE):raise RuntimeError('UNKNOWN_EXECUTION_MODE')
    return mode

def require_scope(root):
    root=Path(root).resolve()
    if execution_mode()!=MODE or root!=Path('/repo') or Path.home()!=Path('/home/research'):
        raise RuntimeError('LOCAL_SCOPE_REQUIRED')
    marker=json.loads(Path('/qualification.json').read_text())
    if marker.get('mode')!=MODE or marker.get('network_namespace')!=os.readlink('/proc/self/ns/net'):
        raise RuntimeError('ISOLATION_ATTESTATION_MISMATCH')
    for name,digest in marker['source_hashes'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('SOURCE_PROVENANCE_MISMATCH: '+name)
    return root

def git(root,*args):
    # Geen generieke arbitrary-command escape vanuit deze capability.
    allowed={('remote',),('diff','--cached','--name-only','--'),('status','--porcelain'),('rev-parse','HEAD'),('add','--all','--','knowledge','hourly-reports'),('commit','-m','research: isolated hourly durable checkpoint')}
    if args not in allowed:raise RuntimeError('LOCAL_GIT_OPERATION_FORBIDDEN')
    env={'PATH':'/usr/bin:/bin','HOME':'/home/research','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_ALLOW_PROTOCOL':'','GIT_TERMINAL_PROMPT':'0'}
    return subprocess.run(['/usr/bin/git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',*args],cwd=root,env=env,capture_output=True,text=True,check=True,timeout=60).stdout.strip()

def preflight(root):
    root=require_scope(root)
    if git(root,'remote'):raise RuntimeError('LOCAL_REMOTE_PRESENT')
    if git(root,'diff','--cached','--name-only','--'):raise RuntimeError('git index is not empty')
    if git(root,'status','--porcelain'):raise RuntimeError('LOCAL_WORKTREE_NOT_CLEAN')
    return {'status':'READY','mode':MODE,'head':git(root,'rev-parse','HEAD'),'remote_capability':False}

def checkpoint(root):
    root=require_scope(root)
    if git(root,'remote'):raise RuntimeError('LOCAL_REMOTE_PRESENT')
    if git(root,'diff','--cached','--name-only','--'):raise RuntimeError('git index is not empty')
    # Alleen de geïsoleerde kopie kan wijzigen, inclusief echte requests/agentoutput.
    git(root,'add','--all','--','knowledge','hourly-reports')
    if git(root,'diff','--cached','--name-only','--'):
        git(root,'commit','-m','research: isolated hourly durable checkpoint')
    return {'status':'LOCAL_COMMITTED','mode':MODE,'head':git(root,'rev-parse','HEAD'),'remote_capability':False}
