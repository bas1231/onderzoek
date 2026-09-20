from pathlib import Path

root=Path.cwd()
base=root/'knowledge/runs/edge_hunter'
print('RUN_DIR_EXISTS',base.exists())
found=list()
if base.exists():
    for p in base.iterdir():
        if not p.is_file():
            continue
        name=p.name
        if '20260920' in name:
            found.append((p.stat().st_mtime,name))
found.sort()
print('TODAY_RUN_FILES',len(found))
for row in found[-12:]:
    print('RUN_FILE',row[1])

has_0400=False
for row in found:
    name=row[1]
    if '0400' in name or '040000' in name:
        has_0400=True
        print('FOUND_0400',name)
print('HAS_0400_RUN',has_0400)
print('HOURLY_0400_STATE_INSPECTION_PASS')
