from pathlib import Path
import importlib.util
import json
import os
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
    recon = load('recon_engine', R / 'control/hourly/recon_engine.py')
    market_scanner = load('market_instance_scanner', R / 'control/hourly/market_instance_scanner.py')
    memory = load('memory_context', R / 'control/hourly/memory_context.py')
    hydrator = load('packet_hydrator', R / 'control/hourly/packet_hydrator.py')
    orchestrator = load('agent_orchestrator', R / 'control/hourly/agent_orchestrator.py')
    candidate_queue = load('candidate_queue', R / 'control/hourly/candidate_queue.py')
    scheduler = load('task_shape_scheduler', R / 'control/hourly/task_shape_scheduler.py')
    graph = load('evidence_failure_graph', R / 'control/hourly/evidence_failure_graph.py')
    ai_handoff = load('ai_handoff', R / 'control/hourly/ai_handoff.py')

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

    # Concrete market-instance scan is independent of text/source discovery.
    # It is public/read-only and fail-soft: a temporary venue/API failure is
    # recorded as BLOCKED evidence but does not abort the rest of the hourly run.
    market_scan_data, market_scan_path = market_scanner.run(run['run_id'])

    routing = router.route(run['run_id'])
    market_scanner.inject_routing(routing, market_scan_data)
    routing_path = R / 'knowledge/runs' / (run['run_id'] + '-routing.json')
    routing_path.write_text(json.dumps(routing, indent=2, sort_keys=True) + chr(10))

    recon_data, recon_path = recon.run(run['run_id'], routing_path)
    memory_data, memory_path = memory.build(run['run_id'])

    # One canonical candidate snapshot per cycle: routing, Director handoff and
    # transient reproduction all consume the same point-in-time queue state.
    queue_data = candidate_queue.build_queue(write_candidates=True)

    packet_dir = R / 'knowledge/runs/agent_packets' / run['run_id']
    hunt_ref = recon_data.get('hunt_plans', {}).get('ref')
    hunt_plan_path = (R / hunt_ref) if hunt_ref else None
    hydration_data = hydrator.hydrate_run(
        routing_path,
        packet_dir,
        hunt_plan_path=hunt_plan_path,
    )

    orchestration_data = orchestrator.orchestrate(
        packet_dir,
        candidate_queue=queue_data,
    )

    # Persist graph-style research memory before dispatch. This records what
    # evidence/candidate routing was actually visible to this cycle.
    graph_input_state = graph.record_cycle_inputs(
        run['run_id'],
        routing,
        orchestration_data.get('candidate_routing', []),
    )

    # Task shape is applied after routing/orchestration and before AI bundle
    # compilation so only useful six-domain workers become ready work items.
    schedule_data = scheduler.schedule(packet_dir)

    proof_review_path = candidate_queue.write_proof_review(
        run['run_id'],
        orchestration_data.get('validation_pipeline', {}),
    )

    director_handoff_path = candidate_queue.write_handoff(
        queue_data,
        run['run_id'],
        proof_review_path=proof_review_path,
    )

    # Build before hourly_wake.py. Browser bridge wake/run matching remains a
    # hard dispatch contract.
    ai_bundle, ai_bundle_path = ai_handoff.build(run['run_id'])

    run_path = R / 'knowledge/runs' / (run['run_id'] + '.json')
    current = json.loads(run_path.read_text())
    current['architecture'] = 'E007_SIX_DOMAIN'
    current['permanent_agents'] = [
        'discovery',
        'market_research',
        'mechanics',
        'algebra',
        'red_team_pentest',
        'research_director',
    ]
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
    current['market_instance_scan'] = {
        'status': market_scan_data.get('status'),
        'ref': str(market_scan_path.relative_to(R)),
        'objects_checked': market_scan_data.get('objects_checked', {}),
        'coverage': market_scan_data.get('coverage', {}),
        'change_detection': market_scan_data.get('change_detection', {}),
        'relation_count': market_scan_data.get('relation_count', 0),
        'relation_type_counts': market_scan_data.get('relation_type_counts', {}),
        'gross_positive_screen_count': market_scan_data.get('gross_positive_screen_count', 0),
        'economic_conclusion': market_scan_data.get('economic_conclusion', 'NO_PROVEN_EDGE'),
        'blocker': market_scan_data.get('blocker'),
    }
    current['automated_routing'] = {
        role: len(data.get('evidence', []))
        for role, data in routing.items()
    }
    current['routing_ref'] = str(routing_path.relative_to(R))
    current['recon_scout'] = {
        'ref': str(recon_path.relative_to(R)),
        'objects_checked': recon_data.get('objects_checked', 0),
        'state_counts': recon_data.get('state_counts', {}),
        'watchlist': recon_data.get('watchlist', {}),
        'economic_conclusion': recon_data.get('economic_conclusion', 'NO_PROVEN_EDGE'),
    }
    current['agent_control_plane'] = {
        'architecture': 'E007_SIX_DOMAIN',
        'packet_dir': str(packet_dir.relative_to(R)),
        'hydrated_roles': hydration_data.get('hydrated_roles', []),
        'hydrated_capabilities': hydration_data.get('hydrated_capabilities', []),
        'recon_hunts': hydration_data.get('recon_hunts', {}),
        'orchestration_ref': str((packet_dir / '_orchestration.json').relative_to(R)),
        'task_schedule_ref': str((packet_dir / '_task_schedule.json').relative_to(R)),
        'scheduled_dynamic_workers': schedule_data.get('scheduled_dynamic_workers', []),
        'scheduled_transient_workers': schedule_data.get('scheduled_transient_workers', []),
        'director_handoff_ref': str(director_handoff_path.relative_to(R)),
        'proof_review_ref': str(proof_review_path.relative_to(R)),
        'ai_work_bundle_ref': str(ai_bundle_path.relative_to(R)),
        'ai_work_ready_roles': [
            item.get('agent_id')
            for item in ai_bundle.get('ready_roles', [])
        ],
        'ai_work_job_count': len(ai_bundle.get('ready_roles', [])),
        'validation_pipeline': orchestration_data.get('validation_pipeline', {}),
        'candidate_routing': orchestration_data.get('candidate_routing', []),
        'queue_count': len(queue_data.get('queue', [])),
        'default_economic_conclusion': 'NO_PROVEN_EDGE',
        'live_trading': False,
        'paid_actions': False,
        'wallet_actions': False,
        'openai_api': False,
    }
    current['research_graphs'] = graph_input_state
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
            handle.write('Architecture: E007_SIX_DOMAIN' + chr(10))
            handle.write('Cadence mode: ' + str(cadence_result.get('mode')) + chr(10))
            handle.write('Usable sources: ' + str(quality_data.get('usable_count')) + chr(10))
            handle.write('Low-text-yield sources: ' + str(quality_data.get('low_text_yield_count')) + chr(10))
            handle.write('Matched Git-memory records: ' + str(memory_data.get('matched_memory_count')) + chr(10))
            handle.write('Memory context: ' + str(memory_path.relative_to(R)) + chr(10))
            handle.write(chr(10) + '### Kalshi market-instance contradiction scan' + chr(10))
            handle.write('Status: ' + str(market_scan_data.get('status')) + chr(10))
            handle.write('Objects checked: ' + json.dumps(market_scan_data.get('objects_checked', {}), sort_keys=True) + chr(10))
            handle.write('Coverage: ' + json.dumps(market_scan_data.get('coverage', {}), sort_keys=True) + chr(10))
            handle.write('Semantic changes: ' + json.dumps(market_scan_data.get('change_detection', {}), sort_keys=True) + chr(10))
            handle.write('Relations: ' + str(market_scan_data.get('relation_count', 0)) + chr(10))
            handle.write('Relation types: ' + json.dumps(market_scan_data.get('relation_type_counts', {}), sort_keys=True) + chr(10))
            handle.write('Gross-positive screens pending fees/L2: ' + str(market_scan_data.get('gross_positive_screen_count', 0)) + chr(10))
            handle.write('Market scan evidence: ' + str(market_scan_path.relative_to(R)) + chr(10))
            if market_scan_data.get('blocker'):
                handle.write('Market scan blocker: ' + str(market_scan_data.get('blocker')) + chr(10))
            handle.write('Economic conclusion: ' + str(market_scan_data.get('economic_conclusion', 'NO_PROVEN_EDGE')) + chr(10))
            handle.write(chr(10) + '### Recon Scout preprocessing' + chr(10))
            handle.write('Objects checked: ' + str(recon_data.get('objects_checked', 0)) + chr(10))
            handle.write('State counts: ' + json.dumps(recon_data.get('state_counts', {}), sort_keys=True) + chr(10))
            handle.write('Watchlist changes: ' + json.dumps(recon_data.get('watchlist', {}), sort_keys=True) + chr(10))
            handle.write('Economic conclusion: ' + str(recon_data.get('economic_conclusion', 'NO_PROVEN_EDGE')) + chr(10))
            handle.write('Recon evidence: ' + str(recon_path.relative_to(R)) + chr(10))

            for role, data in routing.items():
                handle.write('- capability ' + role + ': ' + str(len(data.get('evidence', []))) + ' routed evidence items' + chr(10))

            handle.write(chr(10) + '### Six-domain control plane' + chr(10))
            handle.write('Permanent agents: discovery, market_research, mechanics, algebra, red_team_pentest, research_director' + chr(10))
            handle.write('Scheduled domain workers: ' + json.dumps(schedule_data.get('scheduled_dynamic_workers', [])) + chr(10))
            handle.write('Transient workers: ' + json.dumps(schedule_data.get('scheduled_transient_workers', [])) + chr(10))
            handle.write('Director handoff: ' + str(director_handoff_path.relative_to(R)) + chr(10))
            handle.write('AI work bundle: ' + str(ai_bundle_path.relative_to(R)) + chr(10))
            handle.write('AI READY roles: ' + json.dumps([x.get('agent_id') for x in ai_bundle.get('ready_roles', [])]) + chr(10))
            handle.write('Persistent candidate queue: ' + str(len(queue_data.get('queue', []))) + ' nonterminal candidates' + chr(10))
            handle.write('Candidate→domain/capability assignments: ' + str(len(orchestration_data.get('candidate_routing', []))) + chr(10))
            handle.write('Evidence Graph: ' + str(graph_input_state.get('evidence_graph_ref')) + chr(10))
            handle.write('Economic default: NO_PROVEN_EDGE' + chr(10))

    wake_result = subprocess.run(
        [str(R / '.venv/bin/python'), str(R / 'control/hourly/hourly_wake.py')],
        check=False,
    )

    if os.environ.get("PREDICTION_EXECUTION_MODE") == "qualification_local" and wake_result.returncode != 0:
        raise RuntimeError("LOCAL_AI_WAKE_FAILED")

    print(
        run['run_id'],
        sweep_data['success_count'],
        sweep_data['failure_count'],
        quality_data.get('usable_count'),
        memory_data.get('matched_memory_count'),
        market_scan_data.get('relation_count', 0),
        market_scan_data.get('gross_positive_screen_count', 0),
        'E007_SIX_DOMAIN',
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
