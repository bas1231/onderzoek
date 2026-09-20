from pathlib import Path
import json

root = Path.cwd()
terms = ['orderbook','order book','websocket','trade-api','markets','trades','bid','ask','book']
for source in ['kalshi_docs','polymarket_docs']:
    base = root / 'knowledge/documents/text' / source
    print('SOURCE', source)
    if not base.exists():
        print('MISSING')
        continue
    files = sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    for path in files:
        print('FILE', path.name)
        try:
            obj = json.loads(path.read_text(encoding='utf-8'))
            text = obj.get('text') or obj.get('content') or str(obj)
        except Exception:
            text = path.read_text(encoding='utf-8', errors='ignore')
        low = text.lower()
        shown = 0
        for term in terms:
            start = 0
            while shown < 25:
                pos = low.find(term, start)
                if pos < 0:
                    break
                a = max(0, pos - 350)
                b = min(len(text), pos + 900)
                snippet = text[a:b].replace(chr(10), ' ')
                print('TERM', term)
                print(snippet[:1300])
                print('---')
                shown += 1
                start = pos + len(term)
            if shown >= 25:
                break
