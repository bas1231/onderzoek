import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
AGENTS = ROOT / 'AGENTS.md'
BRIDGE = ROOT / 'control/browser_bridge.py'
MARKER = '## Bridge task authoring rules'


def run(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def main():
    result = {
        'task_id': 'CONTROL-PERSIST-E402-AND-AGENTS-RULES-E404',
        'bridge_marker_present': False,
        'agents_changed': False,
        'secret_guard_pass': False,
        'committed': False,
        'pushed': False,
        'live_trading': False,
        'paid_action': False,
        'wallet_action': False
    }

    bridge_text = BRIDGE.read_text(encoding='utf-8', errors='ignore')
    result['bridge_marker_present'] = 'INCIDENT_HYGIENE_E402' in bridge_text
    if not result['bridge_marker_present']:
        result['status'] = 'BLOCKED_E402_MARKER_MISSING'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(20)

    agents_text = AGENTS.read_text(encoding='utf-8')
    if MARKER not in agents_text:
        lines = [
            '',
            '## Bridge task authoring rules',
            '',
            'Voor taken die via de lokale browser/control bridge worden verstuurd gelden de volgende fail-closed regels:',
            '',
            '- Een task met task_class: infrastructure MOET altijd een expliciete build_authorization bevatten voordat de envelope naar /enqueue wordt verstuurd.',
            '- Gebruik voor gewone control-plane infrastructuur minimaal mode: control_plane, build_kind: control_plane, een niet-lege objective en een expliciete lijst capabilities.',
            '- Controleer capabilities tegen control/edge_hunter/warrant_policy.json; forbidden capabilities mogen nooit worden toegevoegd.',
            '- Diagnosepatroon: /discover HTTP 200 + /enqueue HTTP 400 + lifecycle blijft DISCOVERED + geen pending taskfile betekent eerst control/validator.py en control/edge_hunter/build_gate.py controleren. Dit is een pre-enqueue validatiefout, niet automatisch een bridge-, Git- of cadenceprobleem.',
            '- Een NO_ENQUEUE_ACK in dat patroon is een gevolgincident. Los eerst de concrete /enqueue 400-validatiefout op.',
            '- Gebruik in door de bridge gegenereerde Python-jobbestanden GEEN __file__. De browsertransportlaag heeft dit aantoonbaar verminkt tot file, wat een NameError veroorzaakte. Gebruik voor bridge-jobs Path.cwd() omdat de executor met repository-root als working directory werkt.',
            '- Vermijd in bridge-gegenereerde Python-jobbestanden fragiele escaped newline-literals en vergelijkbare quotingconstructies wanneer hetzelfde zonder escapes kan. Gebruik bijvoorbeeld chr(10) en lijsten met regels. De browsertransportlaag heeft eerder een newline-string gesplitst en zo een SyntaxError veroorzaakt.',
            '- Houd bridge-jobcode klein en transport-robuust. Bij een onverwachte executor syntax- of name-error moet eerst worden gecontroleerd of de opgeslagen job exact overeenkomt met de verzonden bron.',
            '- Voor task_class: research geen overbodige build_authorization toevoegen; research-taken worden door de build gate afzonderlijk behandeld.',
            '',
            'Referentie 2026-09-21: E402R1 werd pre-enqueue geweigerd wegens ontbrekende build_authorization; E402R2 werd na enqueue verminkt van __file__ naar file; E403 kreeg een door transport gesplitste newline-string. Deze drie failure modes mogen niet opnieuw worden geïntroduceerd.'
        ]
        AGENTS.write_text(agents_text.rstrip() + chr(10) + chr(10).join(lines) + chr(10), encoding='utf-8')
        result['agents_changed'] = True

    diff = run('git', 'diff', '--', 'AGENTS.md', 'control/browser_bridge.py')
    forbidden = ['BEGIN RSA PRIVATE KEY', 'BEGIN PRIVATE KEY', 'KALSHI_API_KEY_ID=', 'prodkey2.txt']
    result['secret_guard_pass'] = not any(token in diff.stdout for token in forbidden)
    if not result['secret_guard_pass']:
        result['status'] = 'BLOCKED_SECRET_GUARD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(21)

    pre_staged = run('git', 'diff', '--cached', '--name-only')
    pre_names = [line.strip() for line in pre_staged.stdout.splitlines() if line.strip()]
    if pre_names:
        result['status'] = 'BLOCKED_PREEXISTING_STAGED_FILES'
        result['preexisting_staged_paths'] = pre_names
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(22)

    add = run('git', 'add', '--', 'AGENTS.md', 'control/browser_bridge.py')
    if add.returncode != 0:
        result['status'] = 'BLOCKED_GIT_ADD'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(23)

    staged = run('git', 'diff', '--cached', '--name-only')
    names = sorted(line.strip() for line in staged.stdout.splitlines() if line.strip())
    result['staged_paths'] = names
    expected = ['AGENTS.md', 'control/browser_bridge.py']
    if names != expected:
        run('git', 'restore', '--staged', '--', 'AGENTS.md', 'control/browser_bridge.py')
        result['status'] = 'BLOCKED_UNEXPECTED_STAGED_PATHS'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(24)

    commit = run('git', 'commit', '-m', 'control: persist E402 bridge hygiene and authoring rules')
    result['committed'] = commit.returncode == 0
    if not result['committed']:
        result['status'] = 'BLOCKED_COMMIT_FAILED'
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(25)

    push = run('git', 'push', 'origin', 'HEAD:main')
    result['pushed'] = push.returncode == 0
    result['status'] = 'PASS' if result['pushed'] else 'BLOCKED_PUSH_FAILED'
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['pushed'] else 26)


if __name__ == '__main__':
    main()
