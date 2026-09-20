from pathlib import Path
import os

root=Path.cwd()
terms=['E394','197776','428957','anthropic','clob.polymarket.com/books','feeRate','fee_rate','takerOnly']
results=list()
for base,dirs,files in os.walk(root/'control'):
    dirs[:]=[d for d in dirs if d not in {'.git','.venv','pycache'}]
    for name in files:
        p=Path(base)/name
        try:
            if p.stat().st_size>1500000:
                continue
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        score=sum(1 for term in terms if term.lower() in low)
        if score>=2:
            results.append((score,p,text))
results.sort(key=lambda item:(-item[0],str(item[1])))
print('MATCH_COUNT',len(results))
for score,p,text in results[:12]:
    print('FILE',str(p.relative_to(root)),'SCORE',score)
    lines=text.splitlines()
    for n,line in enumerate(lines,1):
        low=line.lower()
        if any(term.lower() in low for term in terms) or 'fee' in low or 'book' in low or 'token' in low or 'ask' in low or 'bid' in low or 'round(' in low:
            print('LINE',n,repr(line)[:3000])
    print('---')
print('ANTHROPIC_PRICING_AUDIT_E409_PASS')
