# Prediction Control Room V0

## Doel

Control Room V0 is een **lokale, read-only observabilitylaag** bovenop de bestaande Prediction Research-OS. Het dashboard maakt zichtbaar wat al in Git en lokale runtime-evidence aanwezig is. Het doet zelf geen research- of marktdata-polls en kan geen task, trade, walletactie of projectmutatie starten.

## Starten

Vanuit de repository-root:

```bash
python -m control.control_room --repo-root .
```

Open daarna lokaal:

```text
http://127.0.0.1:8765
```

De standaardbind is bewust `127.0.0.1`. Publiceer deze V0 niet direct op internet.

## Wat V0 toont

- centrale truth bar met economische status en safety flags uit `agents/registry.json`;
- system-health met fail-closed `UNKNOWN`/`WARNING` bij ontbrekende evidence;
- recente activiteit uit veilige task/lifecycle/resultmetadata en lokale Git-history;
- geregistreerde agentgroepen en, alleen wanneer lokale evidence dat ondersteunt, hun laatst geziene activiteit;
- task/lifecycle-overzicht zonder willekeurige payloadinhoud of secretwaarden;
- Git branch/HEAD/dirty/divergence/recent commits;
- lokale CPU-load, RAM, disk en uptime waar het OS die veilig beschikbaar stelt;
- alerts en provenance: welke bekende bronnen wel/niet aanwezig zijn.

## Bekende lokale bronnen

V0 kijkt alleen naar bestaande lokale data, waaronder waar aanwezig:

- `agents/registry.json`
- `PROJECT_IN_EEN_OOGOPSLAG.md`
- `control/lifecycle/*.json`
- `control/results/**/*.json`
- `control/jobs/**/*.json`
- `knowledge/ai_exchange/requests/**/*.json`
- `knowledge/ai_exchange/responses/**/*.json`
- `knowledge/runs/**/*.json`
- `hourly-reports/**/*.json`
- lokale Git metadata/log
- lokale `/proc`/filesystem hostmetrics

Ontbreken runtimepaden omdat zij untracked/lokaal zijn, dan blijft hun status zichtbaar als missing/UNKNOWN; V0 verzint geen health.

## Safety by construction

De HTTP-server ondersteunt alleen `GET` en `HEAD`. `POST`, `PUT`, `PATCH` en `DELETE` geven `405 Method Not Allowed`.

De snapshotcode selecteert alleen vooraf gedefinieerde metadatafields. Arbitrary payloadvelden, command output, environment, API keys, tokens, credentials en bestandinhoud worden niet als taskdetails doorgegeven aan de browser.

V0 importeert uitsluitend Python-stdlib en bevat geen HTTP-client/poller naar prediction venues of andere externe bronnen.

## Endpoints

- `/` — dashboard
- `/api/health` — health van de dashboardserver zelf
- `/api/snapshot` — volledige veilige read-only snapshot

De browser ververst `/api/snapshot` iedere 2 seconden. Dit is alleen lokaal verkeer naar de dashboardserver.

## Verificatie

```bash
python -m unittest discover -s control/tests -p 'test_control_room.py' -v
python -m compileall -q control/control_room control/tests/test_control_room.py
```

De tests gebruiken een geïsoleerde tijdelijke fixture-repository en controleren onder meer secret-redaction-by-selection, fail-closed ontbrekende evidence en het blokkeren van alle muterende HTTP-verbs.

## Grenzen van V0

V0 is nog geen volledige event bus en bewijst niet dat een geregistreerde agent daadwerkelijk draait wanneer daar geen heartbeat/runtime-evidence voor bestaat. Daarom heet zo'n status expliciet `UNKNOWN_NO_HEARTBEAT`.

Een latere V1 kan, zonder extra venue-polls, een gestandaardiseerde heartbeat/eventfeed toevoegen voor nauwkeuriger Director/Bridge/Executor/agent-liveness, plus Candidate/Research Map en Weather point-in-time provenance.
