import json
import subprocess
from pathlib import Path

ROOT = Path(file).resolve().parents[2]
TARGET = ROOT / 'AGENTS.md'
MARKER = '## Bridge infrastructure authorization rule'
SECTION = '''

## Bridge infrastructure authorization rule

Voor iedere taak die via de lokale browser/control bridge wordt verstuurd geldt fail-closed:

- Een task met task_class: infrastructure MOET altijd een expliciete build_authorization bevatten voordat de envelope naar /enqueue wordt verstuurd.
- Gebruik voor gewone control-plane/infrastructuurwerkzaamheden minimaal mode: control_plane, build_kind: control_plane, een niet-lege objective en een expliciete lijst capabilities.
- Controleer vóór verzending dat de gekozen capabilities niet voorkomen in control/edge_hunter/warrant_policy.json -> forbidden_capabilities.
- Verstuur een infrastructure-task zonder build_authorization nooit als proef; control/validator.py roept authorize_task() aan en weigert deze fail-closed met missing_build_authorization.
- Diagnosepatroon: wanneer /discover HTTP 200 geeft, /enqueue HTTP 400 geeft, de lifecycle op DISCOVERED blijft en geen pending taskfile ontstaat, controleer eerst Pydantic/control/validator.py/control/edge_hunter/build_gate.py. Dit is dan een pre-enqueue validatiefout, niet automatisch een bridge-, Git- of work-cadenceprobleem.
- Een NO_ENQUEUE_ACK na dit patroon is een gevolgincident; los eerst de concrete /enqueue 400-validatiefout op voordat bridge-processen, Git-state of cadence opnieuw worden gewijzigd.
- Voor task_class: research mag geen overbodige build_authorization worden toegevoegd; de build gate behandelt research-taken afzonderlijk.

Referentie-incident: E402R1 op 2026-09-21. Root cause: infrastructure-envelope zonder build_authorization; /discover werkte, maar /enqueue werd door de validator met HTTP 400 afgewezen.
'''


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main():
    result = {
        'task_id': 'CONTROL-DOCUMENT-INFRA-AUTH-RULE-E403',
        'changed': False,
        'committed': False,
        'pushed': False,
        'live_trading': False,
        'paid_action': False,
        'wallet_action': False
    }

    text = TARGET.read_text(encoding='utf-8')
    if MARKER not in text:
        TARGET.write_text(text.rstrip() + SECTION + '
', encoding='utf-8')
        result['changed'] = True

    diff = run('git', 'diff', '--', 'AGENTS.md')
    forbidden = ['BEGIN RSA PRIVATE KEY', 'BEGIN PRIVATE KEY', 'KALSHI_API_KEY_ID=', 'prodkey2.txt']
    if any(token in diff.stdout for token in forbidden):
        result['status'] = 'BLOCKED_SECRET_GUARD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(20)

    if not result['changed']:
        result['status'] = 'PASS_ALREADY_PRESENT'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0)

    add = run('git', 'add', '--', 'AGENTS.md')
    if add.returncode != 0:
        result['status'] = 'BLOCKED_GIT_ADD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(21)

    staged = run('git', 'diff', '--cached', '--name-only')
    names = [line.strip() for line in staged.stdout.splitlines() if line.strip()]
    result['staged_paths'] = names
    if names != ['AGENTS.md']:
        run('git', 'restore', '--staged', '--', 'AGENTS.md')
        result['status'] = 'BLOCKED_UNEXPECTED_STAGED_PATHS'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(22)

    commit = run('git', 'commit', '-m', 'docs: require infrastructure build authorization in bridge tasks')
    result['committed'] = commit.returncode == 0
    if not result['committed']:
        result['status'] = 'BLOCKED_COMMIT_FAILED'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(23)

    push = run('git', 'push', 'origin', 'HEAD:main')
    result['pushed'] = push.returncode == 0
    result['status'] = 'PASS' if result['pushed'] else 'BLOCKED_PUSH_FAILED'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['pushed'] else 24)


if name == 'main':
    main()
