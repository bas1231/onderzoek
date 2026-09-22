import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
TARGET = 'control/browser_bridge.py'


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main():
    result = {
        'task': 'CONTROL-BRIDGE-INCIDENT-HYGIENE-E402R2',
        'marker_present': False,
        'secret_guard_pass': False,
        'committed': False,
        'pushed': False,
        'live_trading': False,
        'paid_action': False,
        'wallet_action': False
    }

    target = ROOT / TARGET
    text = target.read_text(errors='ignore')
    result['marker_present'] = 'INCIDENT_HYGIENE_E402' in text
    if not result['marker_present']:
        result['status'] = 'BLOCKED_MARKER_MISSING'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(20)

    diff = run('git', 'diff', '--', TARGET)
    forbidden = [
        'BEGIN RSA PRIVATE KEY',
        'BEGIN PRIVATE KEY',
        'KALSHI_API_KEY_ID=',
        'prodkey2.txt'
    ]
    result['secret_guard_pass'] = not any(x in diff.stdout for x in forbidden)
    if not result['secret_guard_pass']:
        result['status'] = 'BLOCKED_SECRET_GUARD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(21)

    add = run('git', 'add', '--', TARGET)
    if add.returncode != 0:
        result['status'] = 'BLOCKED_GIT_ADD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(22)

    staged = run('git', 'diff', '--cached', '--name-only')
    names = [x.strip() for x in staged.stdout.splitlines() if x.strip()]
    result['staged_paths'] = names
    if names != [TARGET]:
        run('git', 'restore', '--staged', '--', TARGET)
        result['status'] = 'BLOCKED_UNEXPECTED_STAGED_PATHS'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(23)

    commit = run('git', 'commit', '-m', 'control: persist bridge incident hygiene E402')
    result['committed'] = commit.returncode == 0
    if not result['committed']:
        result['status'] = 'BLOCKED_COMMIT_FAILED'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(24)

    push = run('git', 'push', 'origin', 'HEAD:main')
    result['pushed'] = push.returncode == 0
    result['status'] = 'PASS' if result['pushed'] else 'BLOCKED_PUSH_FAILED'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['pushed'] else 25)


if __name__ == '__main__':
    main()
