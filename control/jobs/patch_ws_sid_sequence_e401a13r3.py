from pathlib import Path
import json
import subprocess

root = Path.cwd()
market = root / 'control' / 'weather' / 'market_reaction.py'
ws = root / 'control' / 'weather' / 'kalshi_market_reaction_ws.py'
nl = chr(10)
result = {
    'task': 'EDGE-HUNTER-KWI-WS-SEQUENCE-FIX-E401A13R3',
    'tests_pass': False,
    'committed': False,
    'pushed': False,
    'live_trading': False,
    'paid_action': False,
    'wallet_action': False,
    'economic_conclusion': 'NO_PROVEN_EDGE'
}

def run(*args):
    return subprocess.run(args, cwd=root, text=True, capture_output=True)

market_text = market.read_text(encoding='utf-8')
old = nl.join([
    '        if self.last_seq is None or seq != self.last_seq + 1:',
    '            raise ValueError(f"sequence gap: {self.last_seq}->{seq}")'
])
new = nl.join([
    '        # Sequence continuity is validated per WebSocket subscription sid.',
    '        # One sid can multiplex multiple market tickers.'
])
if old in market_text:
    market.write_text(market_text.replace(old, new, 1), encoding='utf-8')
elif 'Sequence continuity is validated per WebSocket subscription sid.' not in market_text:
    result['status'] = 'BLOCKED_MARKET_PATTERN'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(20)

ws_text = ws.read_text(encoding='utf-8')
old_sig = 'def handle_message(books: dict[str, OrderBook], msg: dict[str, Any], recv_at: str, fp) -> None:'
new_sig = 'def handle_message(books: dict[str, OrderBook], msg: dict[str, Any], recv_at: str, fp, last_seq_by_sid: dict[int, int]) -> None:'

if 'def validate_subscription_sequence(' not in ws_text:
    if old_sig not in ws_text:
        result['status'] = 'BLOCKED_SIGNATURE'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(21)
    helper = nl.join([
        'def validate_subscription_sequence(last_seq_by_sid: dict[int, int], msg: dict[str, Any]) -> None:',
        '    sid = msg.get("sid")',
        '    seq = msg.get("seq")',
        '    typ = msg.get("type")',
        '    if typ in ("orderbook_snapshot", "orderbook_delta") and (not isinstance(sid, int) or not isinstance(seq, int)):',
        '        raise ValueError("orderbook frame missing sid/seq")',
        '    if not isinstance(sid, int) or not isinstance(seq, int):',
        '        return',
        '    previous = last_seq_by_sid.get(sid)',
        '    if previous is not None and seq != previous + 1:',
        '        raise ValueError(f"subscription sequence gap sid={sid}: {previous}->{seq}")',
        '    last_seq_by_sid[sid] = seq',
        '',
        '',
        new_sig
    ])
    ws_text = ws_text.replace(old_sig, helper, 1)

anchor = nl.join([
    '    typ = msg.get("type")',
    '    if typ == "orderbook_snapshot":'
])
replacement = nl.join([
    '    typ = msg.get("type")',
    '    try:',
    '        validate_subscription_sequence(last_seq_by_sid, msg)',
    '    except ValueError as exc:',
    '        append_event(fp, {',
    '            "kind": "capture_gap", "start": recv_at, "end": recv_at,',
    '            "reason": f"subscription_sequence:{str(exc)[:200]}", "transport": "ws",',
    '        })',
    '        raise',
    '    if typ == "orderbook_snapshot":'
])
if 'reason": f"subscription_sequence:' not in ws_text:
    if anchor not in ws_text:
        result['status'] = 'BLOCKED_SEQUENCE_ANCHOR'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(22)
    ws_text = ws_text.replace(anchor, replacement, 1)

books_anchor = '    books = {t: OrderBook(t) for t in tickers}'
if 'last_seq_by_sid: dict[int, int] = {}' not in ws_text:
    if books_anchor not in ws_text:
        result['status'] = 'BLOCKED_BOOKS_ANCHOR'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(23)
    ws_text = ws_text.replace(books_anchor, books_anchor + nl + '    last_seq_by_sid: dict[int, int] = {}', 1)

old_call = '            handle_message(books, msg, recv_at, fp)'
new_call = '            handle_message(books, msg, recv_at, fp, last_seq_by_sid)'
if new_call not in ws_text:
    if old_call not in ws_text:
        result['status'] = 'BLOCKED_CALL_ANCHOR'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(24)
    ws_text = ws_text.replace(old_call, new_call, 1)

ws.write_text(ws_text, encoding='utf-8')

compile_result = run(str(root / '.venv' / 'bin' / 'python'), '-m', 'py_compile', str(market), str(ws), 'tests/bridge/test_ws_sid_sequence_e401.py')
if compile_result.returncode != 0:
    result['status'] = 'BLOCKED_COMPILE'
    result['detail'] = compile_result.stderr[-900:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(25)

test = run(str(root / '.venv' / 'bin' / 'python'), 'tests/bridge/test_ws_sid_sequence_e401.py')
result['tests_pass'] = test.returncode == 0
if not result['tests_pass']:
    result['status'] = 'BLOCKED_TEST'
    result['detail'] = test.stderr[-900:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(26)

staged_before = run('git', 'diff', '--cached', '--name-only')
if staged_before.stdout.strip():
    result['status'] = 'BLOCKED_PREEXISTING_STAGED_FILES'
    result['detail'] = staged_before.stdout.splitlines()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(27)

run('git', 'add', '--', 'control/weather/market_reaction.py', 'control/weather/kalshi_market_reaction_ws.py')
commit = run('git', 'commit', '-m', 'weather: validate websocket sequence per subscription')
result['committed'] = commit.returncode == 0
if not result['committed']:
    result['status'] = 'BLOCKED_COMMIT'
    result['detail'] = commit.stderr[-900:]
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(28)

push = run('git', 'push', 'origin', 'HEAD:main')
result['pushed'] = push.returncode == 0
result['status'] = 'PASS' if result['pushed'] else 'BLOCKED_PUSH'
if not result['pushed']:
    result['detail'] = push.stderr[-900:]
print(json.dumps(result, sort_keys=True))
raise SystemExit(0 if result['pushed'] else 29)
