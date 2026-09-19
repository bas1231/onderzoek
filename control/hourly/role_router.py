from pathlib import Path
import json

R = Path.cwd()
POLICY = json.loads((R / 'control/hourly/role_source_policy.json').read_text())
TERMS = {
    'weather_twc': ['metar', '2 metre temperature', 'dewpoint', 'wind component', 'temperature forecast'],
    'microstructure': ['order book', 'matching engine', 'maker rebate', 'taker fee', 'liquidity reward'],
    'behavioral': ['favorite-longshot', 'longshot bias', 'overpriced longshot', 'underpriced favorite', 'probability calibration'],
    'informed_flow': ['informed trading', 'private information', 'insider trading', 'order flow'],
    'algebra': ['mutually exclusive', 'collateral return', 'payout', 'combo', 'synthetic'],
    'settlement': ['settlement', 'resolution rules', 'oracle', 'dispute', 'final settlement'],
    'scout': ['prediction market', 'event contract', 'forecast market'],
}

def route(run_id):
    quality = json.loads((R / 'knowledge/runs' / (run_id + '-source-quality.json')).read_text())
    run = json.loads((R / 'knowledge/runs' / (run_id + '.json')).read_text())
    usable = {x.get('source_id'): x for x in quality.get('sources', []) if x.get('status') == 'USABLE'}
    out = {}
    for role, rule in POLICY.items():
        allowed = set(rule.get('evidence_sources', []))
        hits = []
        for source_id, source in usable.items():
            if source_id not in allowed:
                continue
            ref = source.get('text_ref')
            if not ref:
                continue
            doc = json.loads((R / ref).read_text())
            text = doc.get('text', '')
            lower = text.lower()
            for term in TERMS.get(role, []):
                pos = lower.find(term.lower())
                if pos < 0:
                    continue
                start = max(0, pos - 220)
                stop = min(len(text), pos + 520)
                hits.append({
                    'source_id': source_id,
                    'source_state': run.get('sources', {}).get(source_id),
                    'document_sha256': doc.get('document_sha256'),
                    'retrieved_at': doc.get('retrieved_at'),
                    'term': term,
                    'snippet': ' '.join(text[start:stop].split()),
                })
                break
        out[role] = {
            'status': 'EVIDENCE_ROUTED' if hits else 'NO_EVIDENCE',
            'evidence': hits,
            'coverage_gaps': rule.get('coverage_gaps', []),
        }
    return out

if __name__ == '__main__':
    result = route('hourly-20260920T000000+0200')
    print(json.dumps({ k: len(v.get('evidence', [])) for k, v in result.items() }, indent=2))
