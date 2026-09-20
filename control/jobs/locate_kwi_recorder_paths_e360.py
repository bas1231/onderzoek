from pathlib import Path
import os
import json

root=Path.cwd()
terms=[
    'latest_incomplete',
    'weather_index_watch.py',
    'weather_capture.py',
    'weather_capture_validate.py',
    'KWI-INCOMPLETE-TO-CANONICAL-V1',
    'TASK-WX-002',
    'IMPLEMENTED_LIVE_CAPTURE_PENDING',
    'receipt_basis',
    'config_version'
]
skip={'.git','.venv','pycache'}
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
        matched=[term for term in terms if term.lower() in low]
        if matched:
            hits.append((p,matched,text))

print('MATCHING_FILES',len(hits))
for p,matched,text in hits:
    print('FILE',str(p.relative_to(root)))
    print('MATCHED',','.join(matched))
    shown=0
    for n,line in enumerate(text.splitlines(),1):
        if any(term.lower() in line.lower() for term in terms):
            print('LINE',n,line[:3000])
            shown+=1
            if shown>=30:
                break
    print('---')

candidate=root/'knowledge/candidates/KWI-INCOMPLETE-TO-CANONICAL-V1.json'
if candidate.exists():
    data=json.loads(candidate.read_text(encoding='utf-8'))
    print('CANDIDATE_KEYS',sorted(data.keys()))
    print('CANDIDATE_JSON',json.dumps(data,sort_keys=True)[:12000])

parent=root.parent
print('ROOT',root)
print('PARENT',parent)
for p in sorted(parent.iterdir(),key=lambda x:x.name.lower()):
    if p.is_dir():
        low=p.name.lower()
        if 'proof' in low or 'weather' in low or 'prediction' in low:
            print('SIBLING_DIR',p.name)

print('KWI_RECORDER_PATH_LOCATE_PASS')
