# Prediction Research Browser Bridge

Local Chrome/Chromium extension.

Purpose:

ChatGPT assistant message
-> explicit bridge task block
-> localhost bridge
-> Git commit
-> WSL executor
-> result/evidence
-> Git
-> localhost outbox
-> automatic user result message back to ChatGPT

Security:

- only an explicitly armed ChatGPT conversation is active;
- bridge token is kept in Chrome local extension storage;
- localhost only;
- no OpenAI API;
- no Codex;
- no GitHub connector in the bridge transport itself;
- central research pause remains authoritative;
- local validator/executor gates remain authoritative.

Canonical documentation:

- `control/BRIDGE_ARCHITECTURE_AND_LESSONS.md` — volledige architectuur, lifecycle, securitygrenzen, diagnosevolgorde en geleerde lessen.
- `control/BRIDGE_INCIDENT_LEDGER.md` — append-only incidenthistorie zodat dezelfde failure modes niet opnieuw worden geïntroduceerd.

Harde operationele regel: een bridge-task telt pas als verzonden wanneer de taskmarker daadwerkelijk zichtbaar staat in de gewone assistant-chattekst. Commentary/tool-output alleen is geen betrouwbaar transportoppervlak voor de content script scanner.
