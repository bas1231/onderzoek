from pathlib import Path
import json

root=Path.cwd()
base=root/'knowledge/raw/market_data/polymarket_neg_risk_scans'
files=sorted(base.glob('*batch_e297.json'),key=lambda p:p.stat().st_mtime)
if not files:
    raise SystemExit('batch_result_missing')

path=files[-1]
data=json.loads(path.read_text(encoding='utf-8'))
results=data.get('results',[])
print('PATH',path)
print('RESULT_COUNT',len(results))
priced=0
positive=0
for row in results:
    status=row.get('status')
    title=str(row.get('title',''))
    print('GROUP',row.get('event_id'),status,title[:180])
    if status=='PRICED':
        priced+=1
        yes=float(row.get('yes_gross_edge',0))
        no=float(row.get('no_gross_edge',0))
        if yes>0 or no>0:
            positive+=1
        print('MARKETS',row.get('market_count'))
        print('YES_EDGE',yes,'YES_SIZE',row.get('yes_top_size'))
        print('NO_EDGE',no,'NO_SIZE',row.get('no_top_size'))
    else:
        print('DETAIL',str(row)[:1000])
print('PRICED_GROUPS',priced)
print('GROSS_POSITIVE_GROUPS',positive)
print('NEG_RISK_BATCH_INSPECTION_PASS')
