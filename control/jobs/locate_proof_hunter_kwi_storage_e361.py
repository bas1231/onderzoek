from pathlib import Path
import os

home=Path.home()
print('HOME',home)

repos=list()
for p in home.iterdir():
    if not p.is_dir():
        continue
    low=p.name.lower()
    if 'proof_hunter' in low or 'proof-hunter' in low or low=='proof_hunter':
        repos.append(p)

print('PROOF_REPO_COUNT',len(repos))
for repo in sorted(repos,key=lambda p:p.name):
    print('REPO',repo)
    targets=[
        repo/'proof_hunter/source_lock/weather_index_watch.py',
        repo/'proof_hunter/source_lock/weather_capture.py',
        repo/'proof_hunter/source_lock/weather_capture_validate.py',
        repo/'proof_hunter/venues/kalshi_weather.py'
    ]
    for target in targets:
        print('TARGET',target,'EXISTS',target.exists())
        if not target.exists():
            continue
        text=target.read_text(encoding='utf-8',errors='replace')
        lines=text.splitlines()
        needles=['raw','archive','capture','weather_index','output','data_dir','root','path','mkdir','jsonl','snapshot','manifest']
        shown=0
        for n,line in enumerate(lines,1):
            lowline=line.lower()
            if any(needle in lowline for needle in needles):
                print('LINE',n,line[:3000])
                shown+=1
                if shown>=120:
                    break
        print('---')

print('TOP_LEVEL_POSSIBLE_DATA_DIRS')
for p in sorted(home.iterdir(),key=lambda p:p.name.lower()):
    if not p.is_dir():
        continue
    low=p.name.lower()
    if 'weather' in low or 'data' in low or 'capture' in low or 'proof' in low:
        print('DIR',p)

print('KWI_STORAGE_LOCATE_PASS')
