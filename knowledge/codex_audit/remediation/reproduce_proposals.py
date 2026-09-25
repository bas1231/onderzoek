#!/usr/bin/env python3
"""Reproduceer voorstellen uit duurzame evidence; wijzig nooit productiecode."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / 'proposal_manifest.json').read_text())
for row in manifest['paths']:
    p = ROOT / row['path']
    original = p.read_bytes() if p.exists() else b''
    proposed = HERE / 'proposed' / row['path']
    if p.exists() != row['base_exists'] or hashlib.sha256(original).hexdigest() != row['base_sha256']:
        raise SystemExit('STOP: bron gewijzigd: ' + row['path'])
    if hashlib.sha256(proposed.read_bytes()).hexdigest() != row['proposed_sha256']:
        raise SystemExit('STOP: voorstelhash ongeldig: ' + row['path'])
with tempfile.TemporaryDirectory(prefix='codex-audit-replay-') as tmp:
    fixture = Path(tmp)
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    for name in filter(None, names):
        src = ROOT / name
        if src.is_file():
            dst = fixture / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for row in manifest['paths']:
        dst = fixture / row['path']
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / 'proposed' / row['path'], dst)
    subprocess.run(['git', 'init', '-q'], cwd=fixture, check=True)
    subprocess.run(['git', '-c', 'user.name=Audit fixture', '-c', 'user.email=audit@example.invalid', 'commit', '--allow-empty', '-qm', 'test fixture metadata'], cwd=fixture, check=True)
    # Runner bewaart command, tijden, exitstatus en log buiten deze tijdelijke kopie.
    subprocess.run(['python3', str(HERE / 'run_tests.py'), str(fixture), 'durable_replay', 'tests', 'control/weather', 'control/tampermonkey_multichat', 'knowledge/codex_audit/evidence/test_audit_regressions.py'], cwd=ROOT, check=True)
print('Reproductie afgerond; beoordeel durable_replay.json/log. Tijdelijke kopie opgeruimd.')
raise SystemExit(json.loads((HERE / 'durable_replay.json').read_text())['exit_code'])
