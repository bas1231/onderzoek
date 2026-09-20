from pathlib import Path
import importlib.util
import json
import subprocess
import sys

R = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def main() -> int:
    cadence = load('work_cadence', R / 'control/hourly/work_cadence.py')
    cadence_result = cadence.check(reason='hourly_research_cycle')
    if not cadence_result.get('allowed'):
        print(json.dumps({
            'ok': True,
            'status': 'COOLDOWN_SKIP',
            'cadence': cadence_result,
            'live_trading': False,
            'paid_actions': False,
            'wallet_actions': False,
        }, sort_keys=True))
        return 75

    runner = load('agent_runner', R / 'control/hourly/agent_runner.py')
    sweep = load('source_sweep', R / 'control/hourly/source_sweep.py')
    apply_sweep = load('apply_sweep', R / 'control/hourly/apply_sweep.py')
    extractor = load('extract_text', R / 'control/hourly/extract_text.py')
    quality = load('source_quality', R / 'control/hourly/source_quality.py')
    router = load('role_router', R / 'control/hourly/role_router.py')
    memory = load('memory_context', R / 'control/hourly/memory_context.py')
    hydrator = load('packet_hydrator', R / 'control/hourly/packet_hydrator.py')
    orchestrator = load('agent_orchestrator', R / 'control/hourly/agent_orchestrator.py')
    candidate_queue = load('candidate_queue', R / 'control/hourly/candidate_queue.py')

    run, manifest, report, packets = runner.create_packets()
    sweep_path, sweep_data = sweep.sweep(max_workers=4)
    apply_sweep.apply()

    for item in sweep_data['results']:
        if not item.get('ok'):
            continue
        try:
            extractor.extract(item['source_id'])
        except Exception:
            pass

    quality_data, quality_path = quality.grade(run['run_id'])
    routing = router.route(run['run_id'])
    routing_path = R / 'knowledge/runs' / (run['run_id'] + '-routing.json')
    routing_path.write_text(json.dumps(routing, indent=2, sort_keys=True) + chr(10))

    memory_data, memory_path = memory.build(run['run_id'])

    # PVA AGENT CONTROL PLANE V1
    #
    # Routing evidence is attached to specialist packets first.
    # The orchestrator then assigns READY/NO_EVIDENCE/etc.
    # Candidate scheduling remains persistent and non-blocking.
    # No AI/API call is performed here: ChatGPT remains the
    # Research Director reasoning layer.
    packet_dir = R / 'knowledge/runs/agent_packets' / run['run_id']

    hydration_data = hydrator.hydrate_run(
        routing_path,
        packet_dir,
    )

    orchestration_data = orchestrator.orchestrate(
        packet_dir,
    )

    queue_data = candidate_queue.build_queue(
        write_candidates=True,
    )

    director_handoff_path = candidate_queue.write_handoff(
        queue_data,
        run['run_id'],
    )

    run_path = R / 'knowledge/runs' / (run['run_id'] + '.json')
    current = json.loads(run_path.read_text())
    current['cadence'] = {
        'mode': cadence_result.get('mode'),
        'work_started_at': cadence_result.get('work_started_at'),
        'work_until': cadence_result.get('work_until'),
        'cooldown_until': cadence_result.get('cooldown_until'),
    }
    current['source_quality'] = {
        'usable_count': quality_data.get('usable_count'),
        'low_text_yield_count': quality_data.get('low_text_yield_count'),
        'ref': str(quality_path.relative_to(R)),
    }
    current['automated_routing'] = {
        role: len(data.get('evidence', []))
        for role, data in routing.items()
    }
    current['routing_ref'] = str(routing_path.relative_to(R))
    current['agent_control_plane'] = {
        'packet_dir': str(packet_dir.relative_to(R)),
        'hydrated_roles': hydration_data.get('hydrated_roles', []),
        'orchestration_ref': str(
            (packet_dir / '_orchestration.json').relative_to(R)
        ),
        'director_handoff_ref': str(
            director_handoff_path.relative_to(R)
        ),
        'queue_count': len(queue_data.get('queue', [])),
        'default_economic_conclusion': 'NO_PROVEN_EDGE',
        'live_trading': False,
        'paid_actions': False,
        'wallet_actions': False,
    }
    current['memory_context'] = {
        'ref': str(memory_path.relative_to(R)),
        'matched_memory_count': memory_data.get('matched_memory_count'),
        'active_candidate_count': len(memory_data.get('active_candidate_refs', [])),
        'recent_report_count': len(memory_data.get('recent_hourly_report_refs', [])),
    }
    run_path.write_text(json.dumps(current, indent=2, sort_keys=True) + chr(10))

    report_path = R / 'hourly-reports' / (run['run_id'] + '.md')
    marker = '## Automated preparation'
    existing = report_path.read_text(errors='replace') if report_path.exists() else ''
    if marker not in existing:
        with report_path.open('a') as handle:
            handle.write(chr(10) + marker + chr(10) + chr(10))
            handle.write('Cadence mode: ' + str(cadence_result.get('mode')) + chr(10))
            handle.write('Usable sources: ' + str(quality_data.get('usable_count')) + chr(10))
            handle.write('Low-text-yield sources: ' + str(quality_data.get('low_text_yield_count')) + chr(10))
            handle.write('Matched Git-memory records: ' + str(memory_data.get('matched_memory_count')) + chr(10))
            handle.write('Memory context: ' + str(memory_path.relative_to(R)) + chr(10))
            for role, data in routing.items():
                handle.write('- ' + role + ': ' + str(len(data.get('evidence', []))) + ' routed evidence items' + chr(10))

            handle.write(chr(10) + '### Agent control plane' + chr(10))
            handle.write(
                'Director handoff: '
                + str(director_handoff_path.relative_to(R))
                + chr(10)
            )
            handle.write(
                'Persistent candidate queue: '
                + str(len(queue_data.get('queue', [])))
                + ' nonterminal candidates'
                + chr(10)
            )
            handle.write(
                'Economic default: NO_PROVEN_EDGE'
                + chr(10)
            )

    subprocess.run(
        [str(R / '.venv/bin/python'), str(R / 'control/hourly/hourly_wake.py')],
        check=False,
    )

    print(
        run['run_id'],
        sweep_data['success_count'],
        sweep_data['failure_count'],
        quality_data.get('usable_count'),
        memory_data.get('matched_memory_count'),
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
