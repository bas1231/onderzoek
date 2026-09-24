#!/usr/bin/env python3
from pathlib import Path
import json

HOME = Path.home()
ROOTS = [
    HOME / 'prediction_research_prod',
    HOME / 'prediction_research_recon',
    HOME / 'proof_hunter',
    HOME / 'surplus_maker',
    HOME / 'predictionbot_scan',
]
TERMS = ('health', 'status', 'heartbeat', 'scheduler', 'orchestr', 'agent', 'watch', 'service', 'timer', 'runner')

def collect():
    out = []
    for root in ROOTS:
        if not root.is_dir():
            continue
        for base in (root, root / 'control', root / 'scripts', root / 'systemd'):
            if not base.is_dir():
                continue
            try:
                items = sorted(base.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                continue
            for p in items[:200]:
                name = p.name.lower()
                if any(t in name for t in TERMS):
                    out.append(str(p))
                    if len(out) >= 80:
                        return out
    unit_dir = HOME / '.config/systemd/user'
    if unit_dir.is_dir():
        for p in sorted(unit_dir.iterdir(), key=lambda p: p.name.lower()):
            if any(t in p.name.lower() for t in TERMS):
                out.append(str(p))
                if len(out) >= 80:
                    break
    return out

print(json.dumps({'schema':'PRED_INVENTORY_V1','matches':collect()}, separators=(',', ':')))
