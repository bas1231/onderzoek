from pathlib import Path
import json

R = Path(__file__).resolve().parents[2]

def grade(run_id):
    run_path = R / 'knowledge/runs' / (run_id + '.json')
    run = json.loads(run_path.read_text())
    rows = []
    for source_id, manifest_ref in run.get('source_manifests', {}).items():
        manifest = json.loads(Path(manifest_ref).read_text())
        sha = manifest.get('sha256')
        text_path = R / 'knowledge/documents/text' / source_id / (str(sha) + '.json')
        chars = 0
        if text_path.exists():
            chars = int(json.loads(text_path.read_text()).get('chars') or 0)
        status = 'USABLE' if chars >= 500 else 'LOW_TEXT_YIELD'
        rows.append({
            'source_id': source_id,
            'status': status,
            'chars': chars,
            'document_sha256': sha,
            'text_ref': str(text_path.relative_to(R)) if text_path.exists() else None,
        })
    out = {
        'run_id': run_id,
        'usable_count': sum(1 for row in rows if row.get('status') == 'USABLE'),
        'low_text_yield_count': sum(1 for row in rows if row.get('status') == 'LOW_TEXT_YIELD'),
        'sources': rows,
        'rule': 'LOW_TEXT_YIELD may not support a research claim',
    }
    quality_path = R / 'knowledge/runs' / (run_id + '-source-quality.json')
    quality_path.write_text(json.dumps(out, indent=2, sort_keys=True) + chr(10))
    return out, quality_path
