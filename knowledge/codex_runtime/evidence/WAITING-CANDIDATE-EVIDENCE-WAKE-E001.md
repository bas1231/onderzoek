# WAITING-CANDIDATE-EVIDENCE-WAKE-E001 — uitvoering en status

**Status:** `REQUIRES_HIGH_INTELLIGENCE_REVIEW`
**Acceptatie:** niet uitgevoerd; Tier-A-review door `highest_available_model` met de hoogste beschikbare reasoning-instelling is verplicht.
**Wetenschappelijke status:** `NO_PROVEN_EDGE` (ongewijzigd).
**Veiligheid:** live trading=false; paid actions=false; wallet actions=false; remote push=false.

## 1. Huidig gedrag vóór de wijziging

`candidate_dispatch.select_task()` maakte de taakversie uit de kandidaat en de expliciet gerefereerde evidence. Een bestaand overlay met onder meer `WAITING_FOR_DATA`, `WAITING_FOR_RESULT`, `PARKED` of `NEEDS_REVISION` werd voor dezelfde versie overgeslagen. `resume_condition` en `resurrection_condition` werden in kandidaatrecords/schema's bewaard, maar waren geen deterministische wake-trigger.

`operations.deliver()` valideerde de echte hourly-response en schreef `NEXT_ACTIONS.json` en `AUTO_APPLIED.json`. `candidate_decisions` werden niet generiek aan overlays gekoppeld. De AI-tekst kan dat ook niet veilig doen: zij is geen getypeerde bron van waarheid. Daardoor kon hourly/evaluator-evidence duurzaam aanwezig zijn terwijl een wachtend overlay ongewijzigd bleef en de Director die evidence nooit opnieuw zag.

Een wijziging aan kandidaat/protocol/referenced-evidence kon al een nieuwe taakversie geven, maar een kandidaat in niet-actionable bronstatus werd niet opnieuw aangeboden. Gewone hourlydata veranderde de hash van een kandidaat niet. Dus: ja, relevante evidence kon worden gemist; in de oude flow kon dat onbeperkt/permanent gebeuren.

## 2. Root cause en actuele repository-evidence

De bewezen oorzaak was het ontbreken van een deterministische koppeling tussen **nieuwe, gehashte evidence**, de wait-conditie en een nieuwe idempotente reviewtaak, plus de dispatchfilter die wachtende bronstatussen uitsloot. De hourly-delivery bevat geen candidate-overlay apply/wake-pad. De bekende wait/resurrection-velden waren dus opslag, geen werkende subscriptions.

De actuele vier canaries wijken deels af van de opgegeven statusbeschrijving. Brondata is niet gewijzigd:

| Kandidaat | Bronstatus nu | Bestaand overlay nu | Getypeerde conditie |
|---|---|---|---|
| `KWI-FULL-STATION-PRECANONICAL-V1` | `WAITING_FOR_RESULT` | Geen overlay gevonden | `resume_condition=null` |
| `ASSET-RANK-MAKER-HEDGE-V1` | `RUNNING` | Geen overlay gevonden | `resume_condition=null` |
| `PAYOFF-IDENTITY-MINING-V1` | `NEEDS_DIRECTOR` | `WAITING_FOR_DATA` | `resume_condition=null` |
| `MANUAL-SCOUT-HENGELTJES-20260924` | `EXPERIMENT_REQUIRED` | `NEEDS_REVISION` | `resurrection_condition=null` |

Voor deze echte kandidaten kan de nieuwe trigger dus nog geen evidence-match uitvoeren: zonder machineleesbare conditie zou een automatische classificatie gokken. De huidige uurcollecties/evaluatoruitvoer publiceren bovendien nog geen `PVA_CANDIDATE_EVIDENCE_V1` records met hash-gebonden immutable manifests. Oude evaluatorbestanden of `candidate_decisions` zijn niet achteraf als nieuwe point-in-time wake-evidence geclassificeerd.

## 3. Wijziging en generieke state-machine

`control/codex_supervisor/evidence_wake.py` registreert niet-actionable bronkandidaten alleen als hun `resume_condition`/`evidence_wake_condition` of `resurrection_condition` een geldig `PVA_EVIDENCE_WAKE_CONDITION_V1` object is met cutoff. Het bestand wijzigt kandidaatbronnen niet.

De supervisor scant uitsluitend de afgesproken evidence-roots en accepteert alleen `PVA_CANDIDATE_EVIDENCE_V1` plus een hash-gebonden `PVA_IMMUTABLE_EVIDENCE_MANIFEST_V1`. Symlinks, buiten-roots, naïeve/ongeldige tijden, backfill, onmogelijke retrieval/archive/availability-chronologie, verkeerde kandidaat/kind/status, onvoldoende criteria, ontbrekende hashvelden en pre-cutoff availability wekken niet. KWI-achtige group gates kunnen minimumaantallen per groep eisen; fill-resultaten kunnen conservatieve bewijs- en hashvelden eisen. `NEEDS_REVISION` gebruikt alleen een getypeerde protocol-revision-conditie; anders kan een gewijzigde kandidaat/protocolhash zelf een nieuwe reviewversie opleveren. Gewone hourly-evidence voldoet daar niet aan.

Een match leidt tot:

`EVIDENCE_DISCOVERED → EVIDENCE_MATCHED → CANDIDATE_WAKE_RECORDED → NEXT_TASK_SELECTED → TASK_QUEUED → WORKER_START → RESULT_APPLIED_NEXT_ACTION_RECORDED`

Het atomische wake-record legt kandidaat, oude overlay en hash, vorige status, conditie, evidence-ref/hash/tijd, availability/archive, cutoff, dedupe key, task/version en `NO_PROVEN_EDGE` vast. Dedupe is kandidaat + conditiehash + evidencehash. Het wake-record wordt vóór queue-insert geschreven; herstart geeft dezelfde taak-ID. De reviewprompt bevat oude overlay en nieuwe evidence plus manifest. Resultaatvalidatie controleert evidence-, manifest-, candidate-, protocol-, overlay- en wake-record-hashes opnieuw. Modeltekst is uitsluitend data; `next_action` wordt nooit uitgevoerd.

De kandidaatqueue behoudt bestaande prioriteit bij meerdere gelijktijdige wakes. Onveranderde wachtende kandidaten blijven idle. Een gewijzigde candidate/protocol/ref-hash kan een nieuwe reviewversie maken, ook wanneer de bronstatus wachtend is. De supervisor logt nu ook `TASK_QUEUED` en `WORKER_START` voor intern geselecteerde taken.

## 4. Gewijzigde bestanden

- `control/codex_supervisor/evidence_wake.py` — typed matcher, registratie, provenance, cutoff en idempotente wake.
- `control/codex_supervisor/candidate_dispatch.py` — wake-integratie, versieherbeoordeling en source/overlay-validatie.
- `control/codex_supervisor/supervisor.py` — source pinning en queue/worker terminal events.
- `knowledge/codex_runtime/CONFIG.json` — hashes van de geïnstalleerde supervisor, dispatcher en wake-module.
- `tests/codex_supervisor/test_candidate_dispatch.py` — synthetische canaries en failure-injection.
- Deze evidencefolder — charter, contract, testlog, governance-uitkomst en dit verslag.

Er zijn geen kandidaatbestanden, preregistraties of owner-indexbestanden gewijzigd. Geen operationele hourlyrun, echte Director-call of betaalde service is gestart.

## 5. Tests en lokale canaries

Commando:

```text
.venv/bin/pytest -q tests/codex_supervisor tests/hourly/test_candidate_queue.py tests/hourly/test_research_os_six_domain_e007.py
```

Resultaat: **115 passed**, exit 0. Exacte output/tijd staat in `WAITING-CANDIDATE-EVIDENCE-WAKE-E001-tests.log`. `py_compile`, `git diff --check`, runtime source-pin verificatie en `supervisor.py status` slaagden; die status toont nog steeds de bestaande Hengeltjes `NEEDS_REVISION_REQUIRES_NEW_VERSION_AND_REVIEW`-blokkade.

- **KWI-canary:** synthetic 0 scorable/group-pairs wekt niet; synthetic post-cutoff resultaat met minstens 30 scorable pairs in elk van twee groepen wekt één review.
- **ASSET-canary:** synthetic checkpoint met nul full fills wekt niet; synthetic conservatief bewezen full fill met verplichte evidencehash wekt één review.
- **PAYOFF-canary:** hourly weather wekt niet; synthetic statewise portfolio/rule object met hashrefs wekt één review.
- **Hengeltjes-negative-canary:** ordinary hourly evidence wekt `NEEDS_REVISION` niet; een nieuw protocol-revision artifact met andere protocolhash wekt één review.
- **Idempotentie/herstel:** dubbele tick/evidencehash, crash na wake-record vóór enqueue, nieuwe evidencehash, protocol/evidence/overlay-mutatie, cutoff en symlink worden getest; een wachtende kandidaat blokkeert een andere kandidaat niet.
- **Events:** test valideert de genoemde eventvolgorde van discovery tot result-apply.

Dit zijn fixture-canaries, geen bewijs dat de echte kandidaten al evidence publiceren of door echte nieuwe evidence ontwaakt zijn. De huidige echte kandidaatstatussen/condities hierboven zijn ongewijzigd en vereisen expliciete machineleesbare voorwaarden en producer-integratie voordat runtime wake kan plaatsvinden.

## 6. Resterende risico's en blockers

1. Een evaluator/collector moet het getypeerde evidence-object en immutable manifest deterministisch publiceren. Die producer bestaat nog niet voor de genoemde echte kandidaten.
2. De echte kandidaatrecords hebben geen getypeerde wake-condities; gewone `resume_condition`-tekst wordt opzettelijk niet geïnterpreteerd.
3. De manifest- en evidence-schema's zijn lokaal hash/provenance-gecontroleerd; onafhankelijke Tier-A-review moet bevestigen dat produceridentiteit, primaire bronarchivering en cutoff-semantiek voldoende zijn voor iedere toekomstige producer.
4. De governance-charter is na de eerste implementatie-edit vastgelegd; dat is als procesafwijking in het charter vermeld. Validator gaf `ALLOW_GOVERNED_BUILD`, maar dit vervangt geen voorafgaand charter of Tier-A-review.
5. Geen live/runtime evidence toont dat één bestaande KWI/ASSET/PAYOFF/Hengeltjes-kandidaat al door nieuwe echte evidence is ontwaakt. Software-infrastructuur is synthetisch gevalideerd; productieacceptatie is niet verleend.

## 7. Tier-A reviewgate en Git

`control/edge_hunter/autonomous_build_governance.py` valideerde het buildcontract als `ALLOW_GOVERNED_BUILD` (bewijs: `BUILD-GOVERNANCE-WAKE-E001.json`). Dit is geen Tier-A-acceptatie. De onafhankelijke reviewer moet op de uiteindelijke commit controleren: typed condition semantics, source-manifest assurance, cutoff/revision behavior, duplicate/crash behavior, and no-free-text execution. Tot die review blijft status exact:

`REQUIRES_HIGH_INTELLIGENCE_REVIEW`

Geen remote push is uitgevoerd of toegestaan. De path-only implementatie-/test-/evidencecommit is lokaal gemaakt: `2765bbe` (`fix: add candidate evidence wake routing`). De reeds gewijzigde runtime-queue/statusbestanden en overige untracked owner-/runartefacten bleven buiten die commit en zijn niet aangepast.
