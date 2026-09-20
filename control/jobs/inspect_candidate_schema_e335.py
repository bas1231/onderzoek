from pathlib import Path
import json

root=Path.cwd()
schema_path=root/'control/edge_hunter/candidate_schema.json'
if not schema_path.exists():
    raise SystemExit('candidate_schema_missing')
print('SCHEMA_PATH',schema_path)
schema=json.loads(schema_path.read_text(encoding='utf-8'))
print('SCHEMA')
print(json.dumps(schema,indent=2,sort_keys=True)[:20000])

cand_dir=root/'knowledge/candidates'
print('CANDIDATE_DIR_EXISTS',cand_dir.exists())
found=False
if cand_dir.exists():
    for p in sorted(cand_dir.iterdir()):
        if not p.is_file() or p.suffix!='.json':
            continue
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        print('CANDIDATE_FILE',p.name,'ID',data.get('candidate_id'),'HYPOTHESIS',data.get('hypothesis_id'))
        cid=str(data.get('candidate_id') or '')
        hid=str(data.get('hypothesis_id') or '')
        if cid=='PAYOFF-IDENTITY-MINING-V1' or hid=='PAYOFF-IDENTITY-MINING-V1':
            found=True
            print('REFERENCE_CANDIDATE')
            print(json.dumps(data,indent=2,sort_keys=True)[:20000])
print('REFERENCE_FOUND',found)
print('CANDIDATE_SCHEMA_INSPECTION_PASS')
