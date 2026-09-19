from pathlib import Path
for fn,ranges in [('control/browser_bridge.py',[(1,70)]),('control/browser_extension/content.js',[(1,140)])]:
 lines=Path(fn).read_text().splitlines(); print('===',fn,'===')
 for a,b in ranges:
  for i in range(a-1,min(b,len(lines))): print(f'{i+1}: {lines[i]}')