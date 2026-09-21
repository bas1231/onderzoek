from pathlib import Path
import json
from collections import Counter, defaultdict

LOG_DIR = Path.home() / '.local' / 'state' / 'prediction-research' / 'kalshi_market_reaction_logs'
logs = sorted(LOG_DIR.glob('ws-*.ndjson'), key=lambda p: p.stat().st_mtime, reverse=True)

result = {
    'task': 'EDGE-HUNTER-KWI-WS-SEQUENCE-DIAG-E401A12',
    'log_found': bool(logs),
    'gap_reasons': {},
    'sid_types': {},
    'sid_seq_ranges': {},
    'sample_frames': [],
    'per_ticker_seq_jumps': {},
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False,
    'economic_conclusion': 'NO_PROVEN_EDGE'
}

if not logs:
    result['status'] = 'BLOCKED_NO_WS_LOG'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(10)

path = logs[0]
result['log_name'] = path.name

gap_counter = Counter()
sid_types = defaultdict(Counter)
sid_seqs = defaultdict(list)
ticker_seqs = defaultdict(list)

for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
    try:
        event = json.loads(raw)
    except Exception:
        continue

    kind = event.get('kind')
    if kind == 'capture_gap':
        gap_counter[str(event.get('reason'))] += 1

    if kind != 'ws_raw':
        continue

    typ = event.get('type')
    sid = event.get('sid')
    seq = event.get('seq')
    msg = event.get('msg') or {}
    ticker = msg.get('market_ticker') if isinstance(msg, dict) else None

    if sid is not None:
        sid_types[str(sid)][str(typ)] += 1
    if sid is not None and isinstance(seq, int):
        sid_seqs[str(sid)].append(seq)
    if ticker and isinstance(seq, int) and typ in {'orderbook_snapshot', 'orderbook_delta'}:
        ticker_seqs[str(ticker)].append(seq)

    if len(result['sample_frames']) < 40 and typ in {'orderbook_snapshot', 'orderbook_delta', 'trade'}:
        result['sample_frames'].append({
            'type': typ,
            'sid': sid,
            'seq': seq,
            'ticker': ticker
        })

result['gap_reasons'] = dict(gap_counter.most_common(12))
result['sid_types'] = {sid: dict(counts) for sid, counts in sid_types.items()}

for sid, seqs in sid_seqs.items():
    ordered = sorted(seqs)
    result['sid_seq_ranges'][sid] = {
        'count': len(seqs),
        'min': min(seqs),
        'max': max(seqs),
        'unique': len(set(seqs)),
        'contiguous_sorted': ordered == list(range(min(ordered), max(ordered) + 1))
    }

for ticker, seqs in ticker_seqs.items():
    jumps = [b - a for a, b in zip(seqs, seqs[1:])]
    result['per_ticker_seq_jumps'][ticker] = {
        'count': len(seqs),
        'min_jump': min(jumps) if jumps else None,
        'max_jump': max(jumps) if jumps else None,
        'jumps_gt_1': sum(1 for x in jumps if x > 1)
    }

sequence_gap_count = sum(v for k, v in gap_counter.items() if str(k).startswith('delta_reconstruction:ValueError:sequence gap'))
result['sequence_gap_count'] = sequence_gap_count
result['status'] = 'PASS_DIAGNOSED' if sequence_gap_count > 0 else 'PASS_NO_SEQUENCE_GAP_PATTERN'
print(json.dumps(result, sort_keys=True))
raise SystemExit(0)
