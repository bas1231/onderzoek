# Research OS V1 frozen hotfix note

Frozen hotfix reason: static execution audit found that blind Red-Team/Reproducer evidence projection could accept `is_primary_source=true` without any source ID, ref, hash or lineage. A boolean classification is not provenance.

Hotfix scope is deliberately narrow:
- `control/research_os_v1/red_team.py`
- `control/research_os_v1/reproducer.py`
- corresponding two regression tests

New primary freeze head after hotfix: `cb7a675407d5d6f29434c0220d86c45056e995ef`.

The hotfix does not alter economic promotion logic, scheduler policy, worker roles, live-trading policy, paid-action policy or benchmark thresholds. It only makes malformed provenance fail closed.

Validation must be rebuilt from the newest `main` before any PASS claim. PR #21 remains draft / shadow-only / do not merge yet.

Economic default remains `NO_PROVEN_EDGE`.
