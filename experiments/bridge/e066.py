from pathlib import Path
p=Path('control/browser_extension/content.js').read_text().splitlines()
for i,l in enumerate(p,1):
 if 'JSON.parse' in l or '/discover' in l or 'extractTaskBlocks' in l or 'TASK_PARSE_FAILURE' in l: print(i,l[:220])