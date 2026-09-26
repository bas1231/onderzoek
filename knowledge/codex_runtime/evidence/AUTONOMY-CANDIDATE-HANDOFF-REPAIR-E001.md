# Autonome candidate-handoff — bewijs E001

Opgenomen op 26 september 2026. De oorspronkelijke candidatebestanden en preregistratie zijn tijdens deze taak niet gewijzigd.

## Root cause

De Director-task kreeg candidate-JSON mee, maar de bytes van `manual_seed_ref` en `prospective_protocols` ontbraken in de reasoning-input. Een geldig Director-resultaat werd alleen als runreceipt opgeslagen; er was geen idempotente candidate-overlay en geen deterministische vervolgroute naar lokale validatie. Daardoor kon een protocolgebonden kandidaat stil eindigen zonder dat de queue de openstaande stap zichtbaar maakte.

## Hergebruikte architectuur

De bestaande `control/hourly/candidate_queue.py::build_queue(write_candidates=False)` bepaalt kandidaatvolgorde. `control/codex_supervisor/supervisor.py` blijft de enige SQLite-workerqueue en gebruikt de bestaande systemd-timer. Candidatebronnen blijven eigenaar-bestanden; de nieuwe afgeleide status komt in `knowledge/codex_runtime/candidate_states/`. De bestaande algemene executor is niet gebruikt: zijn oude route heeft een Git-pushpad.

## Wijziging en deterministische toestanden

Allowlisted kennisreferenties worden binnen goedgekeurde `knowledge/`-roots opgelost; absolute paden, `..`, symlink-componenten, missende bestanden en bestanden boven 256 KiB worden afgewezen. De exacte bytes en SHA-256-hashes gaan in de prompt en worden na reasoning opnieuw gecontroleerd. Modeltekst blijft data: alleen de vaste enum `WAITING_FOR_DATA`, `WAITING_FOR_RESULT`, `PARKED`, `WATCH`, `NEEDS_BUILD`, `VALIDATION`, `REJECT` of `NEEDS_REVISION` wordt geïnterpreteerd.

Een gevalideerd resultaat wordt compare/idempotency-gestuurd als overlay opgeslagen. Voor een pending preregistered protocol kan alleen de vaste `PROTOCOL_DEATHCHECK_VALIDATION`-operatie worden gepland. Die voert uitsluitend de vastgezette lokale tests uit. Drie lokale testruns worden nadrukkelijk niet als drie prospectieve shadow-runs gerapporteerd. Activatie blijft uit. `NEEDS_REVISION` vereist een nieuwe versie en expliciete herbeoordeling; het eindigt zichtbaar in `QUEUE_BLOCKED`, nooit in onjuiste `QUEUE_EMPTY`.

## Tests

Commando: `.venv/bin/python -m pytest -q tests/codex_supervisor`

Resultaat: **84 passed**, exitcode 0. Het log staat in `autonomy_candidate_repair_tests.log`. De regressies omvatten protocolprompt/hash, onveilige paden en symlinks, wijziging tijdens reasoning, idempotente overlay, vaste lokale dispatch, gate-falen, replaybinding, duurzame validatierapporten, geen activatie, queue-blocking en bestaande supervisor/candidate-queue-contracten.

## Echte timer-canary

1. De systemd-timer koos eerst `PAYOFF-IDENTITY-MINING-V1` op bestaande effectieve rang 1. De geauthenticeerde `gpt-6-astra`-task eindigde en werd als overlay `WAITING_FOR_DATA` toegepast; het candidatebestand bleef ongewijzigd.
2. De volgende timerrun koos automatisch Hengeltjes op rang 2, zonder handmatige enqueue. De prompt bevatte de manual seed en de volledige preregistered protocoltekst; hun exacte hashes staan in de run-task en overlay. De Director leverde een gestructureerd `NEEDS_REVISION`-resultaat.
3. De Director wees op vooraf ontbrekende protocolbeslissingen over onder meer selectie-/zijderegels en meet-/evaluatiedefinities. De bestaande preregistratie is daarom niet aangepast. De volgende timer-scan gaf `QUEUE_BLOCKED` met `NEEDS_REVISION_REQUIRES_NEW_VERSION_AND_REVIEW`; dezelfde afgeronde task werd niet herhaald.

Run-ID Hengeltjes: `CANDIDATE-960dcdb97aae8865-dd56aef8ea2a2d333186e3aa32fd40a4-1-c2ea0d12`. De machineleesbare task/resultaten en overlays staan naast dit rapport in runtime-evidence. De veilige vervolgactie is een nieuwe, afzonderlijk vastgelegde protocolversie met expliciet menselijke researchbeslissingen; de oude preregistratie niet achteraf overschrijven.

## Grenzen en veiligheid

De echte canary stopte terecht vóór BUILD/VALIDATION: de Director vond protocolherziening nodig. De vaste lokale deathcheck/validatieroute is met regressietests bewezen, maar is voor deze Hengeltjes-versie niet automatisch gestart. Er bestaat geen gekwalificeerde read-only raw orderbook sequence/reconnect-collector en geen prospectief bewijs. Daarom is geen activatierecord gemaakt.

`live_trading=false`; `paid_actions=false`; `wallet_actions=false`; `remote_push=false`; `owner_source_mutated=false`; `scientific_status=NO_PROVEN_EDGE`.
