from pathlib import Path
import os

root=Path.cwd()
terms=[
    'KWI-INCOMPLETE-TO-CANONICAL-V1',
    'latest_incomplete',
    '/live_data/weather/',
    'canonical',
    'incomplete',
    'chicago',
    'miami',
    'nyc'
]
skip_parts={'.git','.venv','pycache'}
hits=list()
scanned=0
for base,dirs,files in os.walk(root):
    dirs[:]=[d for d in dirs if d not in skip_parts]
    for name in files:
        p=Path(base)/name
        try:
            if p.stat().st_size>5000000:
                continue
        except Exception:
            continue
        try:
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        scanned+=1
        low=text.lower()
        matched=list()
        for term in terms:
            if term.lower() in low:
                matched.append(term)
        if matched:
            hits.append((p,matched,text))

print('SCANNED_FILES',scanned)
print('MATCHING_FILES',len(hits))
for p,matched,text in hits[:120]:
    print('FILE',str(p.relative_to(root)))
    print('MATCHED',','.join(matched))
    lines=text.splitlines()
    shown=0
    for n,line in enumerate(lines,1):
        line_low=line.lower()
        if any(term.lower() in line_low for term in terms):
            print('LINE',n,line[:2000])
            shown+=1
            if shown>=12:
                break
    print('---')
print('KWI_EVIDENCE_LOCATE_PASS')
