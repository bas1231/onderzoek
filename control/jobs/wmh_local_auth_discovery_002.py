from pathlib import Path
import os

home=Path.home()
print('WMH_AUTH_DISCOVERY_START')

roots=(home,Path('/mnt/c/Users/leonh'))
needles=('KALSHI_API_KEY_ID','KALSHI_PRIVATE_KEY_PATH','KALSHI_API_KEY')
prune={'.git','node_modules','.cache','data','raw','venv','.venv'}

for root in roots:
 if not root.exists():
  continue
 print('SEARCH_ROOT',root)
 for current,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in prune]
  cur=Path(current)
  try:
   rel=cur.relative_to(root)
   if len(rel.parts)>6:
    dirs[:]=[]
    continue
  except Exception:
   pass
  for name in files:
   low=name.lower()
   path=cur/name
   if 'kalshi' in low and low.endswith('.pem'):
    print('KALSHI_PEM_CANDIDATE',path,'SIZE',path.stat().st_size)
   if 'kalshi' in low and path.stat().st_size<200000:
    print('KALSHI_NAMED_FILE',path)

config_roots=(home/'.config',home/'prediction_research')
for root in config_roots:
 if not root.exists():
  continue
 for current,dirs,files in os.walk(root):
  dirs[:]=[d for d in dirs if d not in prune]
  for name in files:
   path=Path(current)/name
   try:
    if path.stat().st_size>200000 or path.suffix.lower()=='.pem':
     continue
    text=path.read_text(encoding='utf-8',errors='ignore')
   except Exception:
    continue
   hits=tuple(token for token in needles if token in text)
   if hits:
    print('CONFIG_TOKEN_SOURCE',path,'TOKENS',','.join(hits))

unit_root=home/'.config/systemd/user'
if unit_root.exists():
 for path in unit_root.glob('*'):
  if not path.is_file():
   continue
  try:text=path.read_text(encoding='utf-8',errors='ignore')
  except Exception:continue
  if 'kalshi' not in text.lower() and 'KALSHI_' not in text:
   continue
  print('SYSTEMD_CANDIDATE',path)
  for raw in text.splitlines():
   line=raw.strip()
   if line.startswith('EnvironmentFile='):
    print('ENVIRONMENT_FILE',line.split('=',1)[1])
   elif line.startswith('Environment='):
    payload=line.split('=',1)[1]
    names=[]
    for part in payload.replace(chr(34),'').split():
     if '=' in part:
      names.append(part.split('=',1)[0])
    if names:
     print('ENVIRONMENT_NAMES',','.join(names))

print('CURRENT_ENV_API_ID_PRESENT',bool(os.environ.get('KALSHI_API_KEY_ID')))
print('CURRENT_ENV_KEY_PATH_PRESENT',bool(os.environ.get('KALSHI_PRIVATE_KEY_PATH')))
print('NETWORK_CALLS',0)
print('SECRET_VALUES_PRINTED',False)
print('WMH_LOCAL_AUTH_DISCOVERY_002_DONE')