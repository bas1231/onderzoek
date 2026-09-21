from pathlib import Path
import json
from collections import Counter, defaultdict

log_dir = Path.home() / '.local' / 'state' / 'prediction-research' / 'kalshi_market_reaction_logs'
logs = sorted(log_dir.glob('ws-*.ndjson'), key=lambda p: p.stat().st_mtime, reverse=True)

result = {
    'task': 'EDGE-HUNTER-KWI-WS-SEQUENCE-DIAG-E401A12R1',
    'log_found': bool(logs),
    'sequence_gap_count': 0,
    'sid_seq_ranges': {},
    'per_ticker_seq_jumps': {},
    'sample_frames': [],
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

gaps = Counter()
sid_seqs = defaultdict(list)
ticker_seqs = defaultdict(list)

for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
    try:
        event = json.loads(raw)
    except Exception:
        continue

    if event.get('kind') == 'capture_gap':
        gaps[str(event.get('reason'))] += 1

    if event.get('kind') != 'ws_raw':
        continue

    typ = event.get('type')
    sid = event.get('sid')
    seq = event.get('seq')
    msg = event.get('msg') or {}
    ticker = msg.get('market_ticker') if isinstance(msg, dict) else None

    if sid is not None and isinstance(seq, int):
        sid_seqs[str(sid)].append(seq)

    if ticker and isinstance(seq, int) and typ in ('orderbook_snapshot', 'orderbook_delta'):
        ticker_seqs[str(ticker)].append(seq)

    if len(result['sample_frames']) < 50 and typ in ('orderbook_snapshot', 'orderbook_delta', 'trade'):
        result['sample_frames'].append({'type': typ, 'sid': sid, 'seq': seq, 'ticker': ticker})

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
        'jumps_gt_1': sum(1 for jump in jumps if jump > 1),
        'max_jump': max(jumps) if jumps else None
    }

result['sequence_gap_count'] = sum(
    count for reason, count in gaps.items()
    if reason.startswith('delta_reconstruction:ValueError:sequence gap')
)
result['top_gap_reasons'] = dict(gaps.most_common(10))
result['status'] = 'PASS_DIAGNOSED'
print(json.dumps(result, sort_keys=True))
raise SystemExit(0)
