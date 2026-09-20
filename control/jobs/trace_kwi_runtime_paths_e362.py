from pathlib import Path
import os
import re
import subprocess

root=Path.cwd()
home=Path.home()
terms=['weather_index','weather-index','live_data/weather','latest_incomplete','kalshi_weather','weather_capture','receipt_basis','config_version']
skip={'.git','.venv','pycache'}

print('REPO_PATH_HITS')
hits=list()
for base,dirs,files in os.walk(root):
    dirs[:]=[d for d in dirs if d not in skip]
    for name in files:
        p=Path(base)/name
        try:
            if p.stat().st_size>8000000:
                continue
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        if not any(term in low for term in terms):
            continue
        abs_paths=sorted(set(re.findall(r'/home/[A-Za-z0-9_./-]+',text)))
        data_lines=list()
        for n,line in enumerate(text.splitlines(),1):
            ll=line.lower()
            if any(term in ll for term in terms) or '/home/' in line or 'data_dir' in ll or 'raw_dir' in ll or 'archive' in ll:
                data_lines.append((n,line))
        hits.append((p,abs_paths,data_lines))

print('MATCHING_FILES',len(hits))
for p,abs_paths,data_lines in hits[:120]:
    print('FILE',str(p.relative_to(root)))
    for value in abs_paths[:20]:
        print('ABS_PATH',value)
    for n,line in data_lines[:20]:
        print('LINE',n,line[:3000])
    print('---')

print('SYSTEMD_USER_UNITS')
unit_dir=home/'.config/systemd/user'
if unit_dir.exists():
    for p in sorted(unit_dir.iterdir(),key=lambda x:x.name):
        if not p.is_file():
            continue
        try:
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        if 'weather' in low or 'kalshi' in low or 'prediction' in low:
            print('UNIT_FILE',p.name)
            for n,line in enumerate(text.splitlines(),1):
                ll=line.lower()
                if line.startswith('ExecStart=') or line.startswith('Environment=') or line.startswith('WorkingDirectory=') or 'weather' in ll or 'kalshi' in ll:
                    print('UNIT_LINE',n,line[:3000])
            print('---')

print('ACTIVE_WEATHER_UNITS')
listing=subprocess.run(['systemctl','--user','list-units','--all','--no-pager'],capture_output=True,text=True,check=False)
for line in listing.stdout.splitlines():
    low=line.lower()
    if 'weather' in low or 'kalshi' in low or 'twc' in low:
        print('UNIT_STATUS',line.strip())

print('TOP_LEVEL_REPO_DIRS')
for p in sorted(root.iterdir(),key=lambda x:x.name.lower()):
    if p.is_dir():
        print('DIR',p.name)

print('KWI_RUNTIME_PATH_TRACE_PASS')
