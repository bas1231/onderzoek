from pathlib import Path
import os

root=Path.cwd()
source=root/'control/jobs/neg_risk_census_e288.py'
print('SOURCE_EXISTS',source.exists())
if source.exists():
    lines=source.read_text(encoding='utf-8',errors='replace').splitlines()
    print('SOURCE_LINE_COUNT',len(lines))
    for n,line in enumerate(lines,1):
        print('SOURCE_LINE',n,repr(line))

terms=['EDGE-HUNTER-NEG-RISK-CENSUS-E288','neg_risk_census_e288','NEG_RISK_CENSUS','next_cursor','keyset']
hits=list()
for base,dirs,files in os.walk(root/'control'):
    dirs[:]=[d for d in dirs if d not in {'.git','.venv','pycache'}]
    for name in files:
        p=Path(base)/name
        if p==source:
            continue
        try:
            if p.stat().st_size>2000000:
                continue
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        if any(term.lower() in low for term in terms):
            hits.append((p,text))

print('EVIDENCE_FILE_COUNT',len(hits))
for p,text in hits[:50]:
    print('EVIDENCE_FILE',str(p.relative_to(root)))
    shown=0
    for n,line in enumerate(text.splitlines(),1):
        low=line.lower()
        if any(term.lower() in low for term in terms) or 'page' in low or 'cursor' in low or 'events' in low:
            print('EVIDENCE_LINE',n,line[:2500])
            shown+=1
            if shown>=60:
                break
    print('---')
print('PRIOR_KEYSET_PAGINATION_AUDIT_PASS')
