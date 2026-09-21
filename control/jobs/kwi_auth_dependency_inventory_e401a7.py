import importlib.util
import json
import os
import sys
from pathlib import Path

downloads = Path('/mnt/c/Users/leonh/Downloads')
systemd_dir = Path('/home/leonh/.config/systemd/user')
home = Path('/home/leonh')

kalshi_files = []
if downloads.is_dir():
    for entry in os.scandir(downloads):
        if entry.is_file() and 'kalshi' in entry.name.lower():
            p = Path(entry.path)
            st = p.stat()
            kalshi_files.append({
                'path': str(p),
                'size': st.st_size,
                'mode': oct(st.st_mode & 511)
            })

systemd_hits = []
if systemd_dir.is_dir():
    for entry in os.scandir(systemd_dir):
        if not entry.is_file():
            continue
        p = Path(entry.path)
        try:
            text = p.read_text(errors='ignore')
        except Exception:
            continue
        names = []
        for token in ('KALSHI_API_KEY_ID', 'KALSHI_PRIVATE_KEY_PATH', 'KALSHI_API_KEY'):
            if token in text:
                names.append(token)
        if names:
            systemd_hits.append({'path': str(p), 'env_names': names})

venvs = [Path('/home/leonh/prediction_research/.venv')]
if home.is_dir():
    for entry in os.scandir(home):
        if entry.is_dir():
            p = Path(entry.path) / '.venv'
            if p.is_dir() and p not in venvs:
                venvs.append(p)

envs = []
for venv in venvs:
    lib = venv / 'lib'
    if not lib.is_dir():
        continue
    for entry in os.scandir(lib):
        if not entry.is_dir():
            continue
        sp = Path(entry.path) / 'site-packages'
        if sp.is_dir():
            envs.append({
                'venv': str(venv),
                'websockets_present': (sp / 'websockets').exists(),
                'cryptography_present': (sp / 'cryptography').exists()
            })

result = {
    'current_python': sys.executable,
    'current_websockets_available': importlib.util.find_spec('websockets') is not None,
    'current_cryptography_available': importlib.util.find_spec('cryptography') is not None,
    'kalshi_candidate_files': kalshi_files,
    'systemd_files_with_kalshi_env_names': systemd_hits,
    'python_envs': envs,
    'credential_values_printed': False,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False
}
print(json.dumps(result, sort_keys=True))
