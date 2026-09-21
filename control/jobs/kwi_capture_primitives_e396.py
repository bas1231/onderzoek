from pathlib import Path
import subprocess
root=Path.home()/'prediction_research'
files=(root/'kalshi_live.py',root/'kalshi_decider.py')
secret_words=('key','secret','token','credential','private','password','signature')
interesting=('websocket','orderbook','order_book','l2','subscribe','market','ticker','trade','bid','ask','requests','http','snapshot')
print('E396_START')
for path in files:
 print('FILE',path,'EXISTS',path.exists())
 if not path.exists():
  continue
 try:
  lines=path.read_text(encoding='utf-8',errors='ignore').splitlines()
 except Exception as exc:
  print('READ_ERROR',path,type(exc).name)
  continue
 print('LINE_COUNT',len(lines))
 emitted=0
 for line in lines:
  low=line.lower()
  if any(word in low for word in secret_words):
   continue
  stripped=line.lstrip()
  if stripped.startswith(('def ','class ','import ','from ')) or any(word in low for word in interesting):
   print('CODE',line[:240])
   emitted+=1
   if emitted>=80:
    print('CODE_TRUNCATED',path)
    break
units=('prediction-research-kalshi-weather-index-recorder.service','prediction-research-kalshi-weather-index-recorder.timer')
for unit in units:
 try:
  proc=subprocess.run(('systemctl','--user','cat',unit),capture_output=True,text=True,timeout=20)
  print('UNIT_NAME',unit,'RC',proc.returncode)
  for line in proc.stdout.splitlines():
   low=line.lower()
   if any(word in low for word in secret_words):
    continue
   if line.startswith(('ExecStart=','Description=','OnCalendar=','OnUnitActiveSec=','Unit=','WorkingDirectory=')):
    print('UNIT_LINE',line)
 except Exception as exc:
  print('UNIT_ERROR',unit,type(exc).name)
print('E396_DONE')