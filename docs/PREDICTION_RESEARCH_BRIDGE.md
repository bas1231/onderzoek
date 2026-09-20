# Prediction Research Bridge

## Doel

Deze bridge verbindt een geautoriseerde ChatGPT-projectchat met de lokale researchomgeving:

`ChatGPT assistantbericht → Chrome-extensie → lokale bridge → Git/WSL executor → outbox → ChatGPT`.

Dit document beschrijft de waargenomen werking en de veilige diagnoseprocedure. Het is geen toestemming om de BUILD FREEZE, kostenregels of tradingbeperkingen te omzeilen.

## ChatGPT-paginadiagnose

Een werkende paginadiagnose hoort onder andere te tonen:

- `assistant_nodes > 0`
- `composer_found: true`
- de juiste ChatGPT-chat in `pathname` / `url`
- `task_start_markers` en `task_end_markers` zodra een gemarkeerde taak zichtbaar is.

De popup-roundtrip is een andere test. Die omzeilt het scannen van de ChatGPT-pagina en test rechtstreeks:

`extensie → bridge → Git → WSL → resultaat`.

Een geslaagde popup-roundtrip bewijst daarom niet automatisch dat assistantberichten op de ChatGPT-pagina worden ontdekt.

## Taakmarkers

De browserextensie zoekt in assistantberichten naar exact deze markers:

```text
<<<PREDICTION_BRIDGE_TASK>>>
<JSON envelope>
<<<END_PREDICTION_BRIDGE_TASK>>>
```

De tekst tussen de markers moet geldige JSON zijn.

Minimaal verwacht de scanner een task-object met een unieke `task_id`:

```json
{
  "task": {
    "task_id": "UNIEKE-TAAK-ID",
    "title": "Korte titel",
    "objective": "Concrete opdracht"
  }
}
```

Ontbreekt `task.task_id`, dan wordt de taak niet normaal geënqueued. Gebruik nooit een eerder verwerkt task-ID voor een nieuwe test.

## Verwachte keten

Bij een normale verwerking hoort een taak conceptueel door deze lifecycle te gaan:

`DISCOVERED → ACCEPTED → RUNNING → COMPLETED → DELIVERED → ACKED`.

De content-scriptlaag ontdekt de marker, meldt discovery bij de lokale bridge en biedt daarna het volledige envelope aan de enqueue-endpoint aan. De lokale executor verwerkt de taak. Resultaten worden via de outbox opgehaald en door de extensie terug in de ChatGPT-composer geplaatst.

## Veilige minimale test

Gebruik voor een connectiviteitstest een nieuwe task-ID en een opdracht zonder bestandswijzigingen, research, trading of betaalde acties. Bijvoorbeeld: uitsluitend `BRIDGE TEST OK` naar stdout schrijven.

Een bridge-test is geen toestemming voor live execution, betaalde API's, walletacties of nieuwe infrastructuur.

## Diagnose in WSL

Zoek een specifieke taak:

```bash
cd ~/prediction_research
grep -Rni --exclude-dir=.git \
  "TAAK-ID-HIER" \
  control ~/.local/state/prediction-research 2>/dev/null
```

Bekijk recente lifecycle/taskbestanden:

```bash
find control/lifecycle control/tasks -type f -mmin -10 \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' 2>/dev/null | sort
```

Bekijk recente state/incidents:

```bash
find ~/.local/state/prediction-research -type f -mmin -10 \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' 2>/dev/null \
  | sort -r | head -50
```

Volg relevante user-journalregels live:

```bash
journalctl --user -f --since "2 minutes ago" \
  | grep --line-buffered -Ei 'bridge|discover|enqueue|task|parse|incident'
```

## Interpretatie van fouten

Als de popup-roundtrip slaagt maar een gemarkeerd assistantbericht nergens in `control/lifecycle`, `control/tasks` of de lokale state verschijnt, ligt het probleem vóór de WSL-executor. Controleer dan eerst:

1. of de juiste chat/project daadwerkelijk armed is;
2. of de markers letterlijk in het gerenderde assistantbericht voorkomen;
3. of de page diagnostic de markers telt;
4. of de content script actief is en de assistant-DOM kan lezen;
5. browserconsole/bridge-incidenten voor parse-, discover- of enqueuefouten.

`NO_ENQUEUE_ACK` betekent dat een taak geen verwachte enqueue-bevestiging kreeg. `RESULT_DELIVERY_STALL` wijst op een probleem bij het terugleveren/acknowledgen van een resultaat. Onderzoek de concrete lifecycle- en incidentbestanden voordat conclusies worden getrokken.

## Taal

Menselijk leesbare testresultaten, statusupdates en activity-logteksten voor de eigenaar op Git worden in het Nederlands geschreven. Technische identifiers, code, bestandsnamen en letterlijke protocolvelden mogen Engels blijven wanneer dat preciezer is.

## Veiligheidsregels

De bestaande repositoryregels blijven leidend. In het bijzonder:

- BUILD FREEZE blijft gelden totdat de eigenaar die expliciet opheft.
- Geen live trading of wallet/crypto-acties zonder expliciete toestemming.
- Geen betaalde actie zonder voorafgaande specifieke toestemming.
- Een connectivity-test moet zo klein mogelijk zijn en mag niet ongemerkt research/buildwerk starten.
