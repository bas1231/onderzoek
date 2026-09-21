from pathlib import Path
import subprocess
roots=(Path.home()/'prediction_research',Path.home()/'proof_hunter',Path.home()/'surplus_maker')
needles=('websocket','orderbook','order_book','l2','subscribe','kalshi')
skip=('credential','private_key','.env','secret','token')
print('E395_START')
for root in roots:
 print('ROOT',root,'EXISTS',root.exists())
 if not root.exists():
  continue
 matches=[]
 for path in root.rglob('*.py'):
  low=str(path).lower()
  if any(word in low for word in skip):
   continue
  try:
   text=path.read_text(encoding='utf-8',errors='ignore').lower()
  except Exception:
   continue
  score=sum(1 for word in needles if word in text or word in path.name.lower())
  if score>=2:
   matches.append((score,path))
 matches.sort(reverse=True,key=lambda item:item)
 print('MATCH_COUNT',len(matches))
 for score,path in matches[:30]:
  print('MATCH',score,path)
  try:
   lines=path.read_text(encoding='utf-8',errors='ignore').splitlines()
  except Exception:
   continue
  emitted=0
  for line in lines:
   low=line.lower()
   if any(word in low for word in skip):
    continue
   if line.lstrip().startswith(('def ','class ','import ','from ')) or any(word in low for word in ('websocket','orderbook','order_book','subscribe','l2')):
    print('LINE',line[:220])
    emitted+=1
    if emitted>=25:
     break
try:
 proc=subprocess.run(('systemctl','--user','list-unit-files','--no-pager','--no-legend'),capture_output=True,text=True,timeout=20)
 for line in proc.stdout.splitlines():
  low=line.lower()
  if any(word in low for word in ('kalshi','surplus','weather','orderbook','proof-hunter')):
   print('UNIT',line)
except Exception as exc:
 print('UNIT_ERROR',type(exc).name)
print('E395_DONE')