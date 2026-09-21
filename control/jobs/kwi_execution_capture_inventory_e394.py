from pathlib import Path
import subprocess
homes=[Path.home()/'prediction_research',Path.home()/'proof_hunter',Path.home()/'surplus_maker']
patterns=('weather_l2','orderbook','websocket','kalshi','l2_capture','trade_capture')
print('E394_INVENTORY_START')
for base in homes:
 print('ROOT',base,'EXISTS',base.exists())
 if not base.exists():
  continue
 count=0
 for path in base.rglob('*'):
  if not path.is_file():
   continue
  name=path.name.lower()
  full=str(path).lower()
  if not any(p in name or p in full for p in patterns):
   continue
  if any(secret in full for secret in ('credential','private_key','bridge_token','.env')):
   continue
  try:size=path.stat().st_size
  except Exception:size=-1
  print('FILE',size,path)
  count+=1
  if count>=120:
   print('TRUNCATED',base)
   break
try:
 out=subprocess.run(['systemctl','--user','list-unit-files','--no-pager','--no-legend'],capture_output=True,text=True,timeout=20)
 for line in out.stdout.splitlines():
  low=line.lower()
  if 'kalshi' in low or 'weather' in low or 'orderbook' in low or 'surplus' in low:
   print('UNIT',line)
except Exception as exc:
 print('SYSTEMD_INVENTORY_ERROR',type(exc).name)
print('E394_INVENTORY_DONE')