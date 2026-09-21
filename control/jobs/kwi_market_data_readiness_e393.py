from pathlib import Path
from datetime import datetime,timezone
root=Path.cwd()
state=Path.home()/'.local/state/prediction-research'
terms=('orderbook','order_book','l2','trade','kxtemp','market')
weather_terms=('weather','kwi','kxtemp','temp')
rows=[]
for base,label in ((state,'state'),(root,'repo')):
 if not base.exists():
  continue
 for path in base.rglob('*'):
  if not path.is_file():
   continue
  text=str(path).lower()
  if not any(term in text for term in terms):
   continue
  if not any(term in text for term in weather_terms):
   continue
  try:
   size=path.stat().st_size
   mtime=datetime.fromtimestamp(path.stat().st_mtime,tz=timezone.utc).isoformat()
  except Exception:
   size=-1;mtime='UNKNOWN'
  rows.append((label,str(path),size,mtime))
rows.sort(key=lambda row:row,reverse=True)
print('KWI_MARKET_DATA_FILE_COUNT',len(rows))
state_count=sum(1 for row in rows if row[0]=='state')
repo_count=sum(1 for row in rows if row[0]=='repo')
print('STATE_FILE_COUNT',state_count)
print('REPO_FILE_COUNT',repo_count)
shown=0
for row in rows:
 if shown>=80:
  break
 label,path,size,mtime=row
 print('CANDIDATE',label,size,mtime,path)
 shown+=1
print('KWI_MARKET_DATA_READINESS_E393_DONE')