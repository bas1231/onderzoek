from pathlib import Path

root = Path.cwd()
terms = ['orderbook','order_book','l2','websocket','kalshi','polymarket','trade','bid','ask']
areas = ['control','experiments','src']
seen = set()
for area in areas:
    base = root / area
    if not base.exists():
        continue
    for path in base.rglob('*.py'):
        if path in seen:
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            continue
        hits = [term for term in terms if term in text]
        if hits:
            print('FILE', path.relative_to(root))
            print('HITS', ','.join(hits))
            for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
                low = line.lower()
                if any(term in low for term in terms):
                    print(line[:500])
            print('END_FILE')
