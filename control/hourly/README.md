# Hourly Research

Hourly autonomous research remains research-only. No live trading, paid APIs, wallet actions or spend without explicit approval.

Canonical plan: `docs/HOURLY_RESEARCH_FACTORY_PVA.md`.

Control flow:

`cadence -> source sweep -> source quality -> role routing -> targeted Git memory -> falsification/reproduction -> Research Director -> Git report`

Key rules:

- Git is the canonical memory and audit trail.
- ChatGPT is the Research Director; this repository does not call the OpenAI API for Director reasoning.
- Every active cycle checks `work_cadence.py` before doing research.
- Four hours of work are followed by one full cooldown hour.
- During cooldown no source sweep, agent packets or Director wake is created.
- Passive local recorders that do not use ChatGPT/OpenAI may continue.
- New evidence is compared with negative evidence, active candidates and recent research through `memory_context.py`.
- `NO_PROVEN_EDGE` remains the default economic conclusion.
- Nieuwe browser-bridge taken en executor-claims worden fail-closed door dezelfde `work_cadence.py` gate gecontroleerd; reeds lopende taken mogen afronden en passieve recorders blijven buiten deze gate.
