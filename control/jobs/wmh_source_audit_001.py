from pathlib import Path
import os
import subprocess

home=Path.home()
roots=(home/'prediction_research',home/'proof_hunter',home/'proof-hunter',home/'proof_trader',home/'surplus_maker',Path('/home/kali/proof_hunter'),Path('/home/kali/proof-hunter'),Path('/home/kali/surplus_maker'))
print('WMH_SOURCE_AUDIT_START')
for root in roots:
 print('ROOT',root,'EXISTS',root.exists())
 if root.exists() and (root/'.git').exists():
  head=subprocess.run(('git','-C',str(root),'rev-parse','HEAD'),capture_output=True,text=True,timeout=10)
  branch=subprocess.run(('git','-C',str(root),'branch','--show-current'),capture_output=True,text=True,timeout=10)
  print('GIT',root,'BRANCH',branch.stdout.strip(),'HEAD',head.stdout.strip())
key=Path('/home/leonh/proof_trader/secrets/kalshi_private.pem')
print('PRIVATE_KEY_EXISTS',key.is_file())
if key.is_file():
 print('PRIVATE_KEY_MODE',oct(key.stat().st_mode & 0o777))
print('API_KEY_ENV_PRESENT',bool(os.environ.get('KALSHI_API_KEY_ID')))
rels=('proof_hunter/venues/kalshi_authenticated.py','proof_hunter/source_lock/weather_l2_capture.py','proof_hunter/source_lock/weather_trade_capture.py','proof_hunter/source_lock/weather_fee_capture.py','proof_hunter/source_lock/weather_index_watch.py','proof_hunter/storage/raw_store.py','PVA.md','ARCHITECTURE.md')
for root in roots:
 if not root.exists():
  continue
 for rel in rels:
  path=root/rel
  if path.is_file():
   print('COMPONENT',path,'SIZE',path.stat().st_size)
keywords=('sequence','websocket','orderbook','trade','replay','settlement','recorder')
seen=0
for root in roots:
 if not root.exists():
  continue
 for path in root.rglob('.py'):
  low=path.name.lower()
  if any(word in low for word in keywords):
   print('CODE_CANDIDATE',path)
   seen+=1
   if seen>=100:
    break
 if seen>=100:
  break
config_roots=(home/'.config',home/'prediction_research',home/'proof_trader')
found=0
for root in config_roots:
 if not root.exists():
  continue
 for path in root.rglob(''):
  if found>=20:
   break
  if not path.is_file():
   continue
  if path.suffix.lower()=='.pem':
   continue
  try:
   if path.stat().st_size>200000:
    continue
   text=path.read_text(encoding='utf-8',errors='ignore')
  except Exception:
   continue
  if 'KALSHI_API_KEY_ID' in text:
   print('API_KEY_ID_SOURCE_CANDIDATE',path)
   found+=1
print('NETWORK_CALLS',0)
print('SECRET_VALUES_PRINTED',False)
print('WMH_SOURCE_AUDIT_001_DONE')