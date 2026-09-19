from pathlib import Path
for fn,needle,before,after in [('control/browser_extension/content.js','JSON.parse(block)',18,95),('control/browser_bridge.py','/discover',45,70)]:
 lines=Path(fn).read_text().splitlines(); idx=next((i for i,l in enumerate(lines) if needle in l),None); print('===',fn,'===');
 if idx is not None:
  for n in range(max(0,idx-before),min(len(lines),idx+after)): print(f'{n+1}: {lines[n]}')