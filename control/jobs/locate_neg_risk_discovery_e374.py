from pathlib import Path
import os
import json

root=Path.cwd()
terms=['E296','neg_risk_manifests','negRisk','negative_risk','non-augmented','non_augmented']
skip={'.git','.venv','pycache'}
hits=list()
for base,dirs,files in os.walk(root/'control'):
    dirs[:]=[d for d in dirs if d not in skip]
    for name in files:
        p=Path(base)/name
        try:
            if p.stat().st_size>3000000:
                continue
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        matched=[term for term in terms if term.lower() in low]
        if matched:
            hits.append((p,matched,text))

print('CONTROL_MATCH_COUNT',len(hits))
for p,matched,text in hits[:100]:
    print('FILE',str(p.relative_to(root)))
    print('MATCHED',','.join(matched))
    shown=0
    for n,line in enumerate(text.splitlines(),1):
        ll=line.lower()
        if any(term.lower() in ll for term in terms) or 'gamma' in ll or 'cursor' in ll or 'offset' in ll or 'limit' in ll:
            print('LINE',n,line[:2500])
            shown+=1
            if shown>=40:
                break
    print('---')

manifest_dir=root/'knowledge/raw/market_data/polymarket_neg_risk_manifests'
print('MANIFEST_DIR_EXISTS',manifest_dir.exists())
if manifest_dir.exists():
    files=[p for p in manifest_dir.iterdir() if p.is_file()]
    files.sort(key=lambda p:p.stat().st_mtime)
    print('MANIFEST_COUNT',len(files))
    for p in files[-5:]:
        print('MANIFEST',p.name,'SIZE',p.stat().st_size)
    if files:
        p=files[-1]
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            data=None
        if isinstance(data,dict):
            print('LATEST_MANIFEST_KEYS',sorted(data.keys()))
            for key in sorted(data.keys()):
                value=data.get(key)
                if isinstance(value,list):
                    print('FIELD',key,'LIST_LEN',len(value))
                    if value:
                        first=value[0]
                        if isinstance(first,dict):
                            print('FIELD_FIRST_KEYS',key,sorted(first.keys()))
                elif isinstance(value,dict):
                    print('FIELD',key,'DICT_KEYS',sorted(value.keys())[:80])
                else:
                    print('FIELD',key,str(value)[:1000])
print('NEG_RISK_DISCOVERY_LOCATE_PASS')
