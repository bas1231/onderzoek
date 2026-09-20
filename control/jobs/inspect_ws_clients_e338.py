from pathlib import Path
import importlib.util

root=Path.cwd()
mods=['websockets','websocket','aiohttp','httpx','requests']
for name in mods:
    spec=importlib.util.find_spec(name)
    print('MODULE',name,'AVAILABLE',spec is not None)
    if spec is not None:
        print('MODULE_PATH',name,str(spec.origin))

for name in ['pyproject.toml','requirements.txt','requirements-dev.txt']:
    p=root/name
    print('DEPENDENCY_FILE',name,'EXISTS',p.exists())
    if p.exists():
        text=p.read_text(encoding='utf-8',errors='replace')
        for line in text.splitlines():
            low=line.lower()
            if 'websocket' in low or 'aiohttp' in low or 'httpx' in low:
                print('DEPENDENCY_LINE',name,line[:500])

hits=list()
for base in [root/'control',root/'src',root/'experiments']:
    if not base.exists():
        continue
    for p in base.rglob('*.py'):
        try:
            text=p.read_text(encoding='utf-8',errors='replace')
        except Exception:
            continue
        low=text.lower()
        if 'ws-subscriptions-clob.polymarket.com' in low or 'websocket' in low or 'websockets.connect' in low:
            hits.append(str(p.relative_to(root)))
print('CODE_HIT_COUNT',len(hits))
for item in sorted(hits)[:80]:
    print('CODE_HIT',item)
print('WS_CLIENT_INSPECTION_PASS')
