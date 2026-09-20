from __future__ import annotations

from pathlib import Path
import json

from control.hourly import memory_context


def test_memory_context_links_candidates_reports_and_prior_knowledge(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / 'repo'
    runs = root / 'knowledge/runs'
    runs.mkdir(parents=True)

    for rel in memory_context.CANONICAL_REFS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('canonical')

    candidate = root / 'candidates/active/C1.yaml'
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text('mechanism: maker rebate order book')

    prior = root / 'knowledge/prior.md'
    prior.parent.mkdir(parents=True, exist_ok=True)
    prior.write_text('Order book depth was shallow in the prior experiment.')

    report = root / 'hourly-reports/20260920T1200.md'
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text('prior hourly report')

    run_id = 'hourly-test'
    routing = {
        'microstructure': {
            'evidence': [{'term': 'order book'}],
        }
    }
    (runs / f'{run_id}-routing.json').write_text(json.dumps(routing))

    monkeypatch.setattr(memory_context, 'ROOT', root)
    monkeypatch.setattr(memory_context, 'RUNS', runs)

    data, out = memory_context.build(run_id)

    assert out.exists()
    assert 'candidates/active/C1.yaml' in data['active_candidate_refs']
    assert 'hourly-reports/20260920T1200.md' in data['recent_hourly_report_refs']
    refs = {item['ref'] for item in data['matched_memory']}
    assert 'candidates/active/C1.yaml' in refs
    assert 'knowledge/prior.md' in refs
    assert data['policy']['negative_evidence_must_be_checked'] is True
    assert data['policy']['raw_tapes_in_git'] is False
