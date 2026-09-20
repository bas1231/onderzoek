# Local Autonomous Execution Rules

Deze regels gelden voor de lokale WSL research-control-plane.

## Doel

De executor voert reproduceerbare researchtaken uit die door de
Prediction Market Research KB worden aangestuurd.

Git is de audit trail.

## Toegestaan

- repository-owned Python uitvoeren;
- tests uitvoeren;
- lokale CPU/GPU gebruiken;
- virtualenv-packages installeren;
- experiment-artifacts produceren;
- resultaten en evidence committen;
- branches en worktrees gebruiken waar nodig.

## Niet toegestaan

- live orders plaatsen;
- live orders annuleren;
- withdrawals uitvoeren;
- crypto of wallets bedienen;
- productie-tradingcredentials gebruiken;
- willekeurige sudo-commando's uitvoeren;
- bestanden buiten goedgekeurde researchlocaties wijzigen.

## Fail closed

Een infrastructuurfout mag niet eindeloos opnieuw worden uitgevoerd.

Bij een fout:
- registreer de fout;
- verplaats de taak naar failed;
- bewaar provenance;
- wacht op analyse of een nieuwe taak.

## Reproduceerbaarheid

Iedere uitgevoerde taak bevat minimaal:
- task_id;
- hypothesis_id;
- source Git commit;
- exact command;
- start- en eindtijd;
- exit code;
- hashes van relevante output;
- RESULT.json.

## Terminal safety

Genereer geen commando's bedoeld om de actieve interactieve shell
van de gebruiker te beëindigen.

Gebruik in instructies aan de gebruiker geen:
- set -e;
- set -euo pipefail;
- exit;
- shell-killing commands;
- shell-replacing exec constructs.

Fouten worden getoond zonder de terminalsessie te beëindigen.

## Centrale research queue

`control/TASK_QUEUE.yaml` blijft de centrale hoog-niveau researchqueue.

Wanneer `queue_status` niet `ACTIVE` is:
- infrastructure-taken mogen worden uitgevoerd;
- research-taken blijven pending;
- de executor mag de researchpauze niet zelfstandig opheffen.

Alleen een expliciete hervatting van het prediction-marketonderzoek
mag de centrale researchqueue activeren.

## Build authorization

Nieuwe `infrastructure`-taken moeten vóór toelating een expliciete
`build_authorization` bevatten. De canonical uitleg en voorbeelden staan in
`control/edge_hunter/BUILD_AUTHORIZATION.md`.

Voor generieke safety/reliability/provenance/control-plane-bouw:
- gebruik `mode: control_plane`;
- gebruik `build_kind: control_plane`;
- geef een begrensd `objective` en de werkelijk benodigde `capabilities` op;
- vraag nooit live trading, order submission, wallet/fund movement, paid actions,
  credential writes of venue write endpoints aan.

Voor candidate-specifieke bouw:
- gebruik `mode: candidate`;
- verwijs met `warrant_ref` naar een bestaand bestand onder `knowledge/warrants/`;
- build kind, objective en capabilities moeten exact overeenkomen met de warrant;
- een gewijzigde candidate, policy, build state of request maakt de warrant ongeldig.

Researchtaken zonder code-/infrastructuurbouw gebruiken geen
`build_authorization` en blijven onder de gewone researchqueue-regels vallen.

## Git sync guard

De lokale executor mag een nieuwe pending task alleen claimen wanneer de
checkout op branch `main` exact gelijk is aan de zojuist gefetchte
`origin/main`.

De guard in `control/git_sync_guard.py` trekt, merget en rebaset nooit
automatisch. De volgende toestanden blokkeren fail-closed:
- `LOCAL_BEHIND`: GitHub bevat commits die lokaal ontbreken;
- `LOCAL_AHEAD`: lokaal bestaan nog commits die niet op GitHub staan;
- `DIVERGED`: lokaal en remote zijn beide onafhankelijk vooruitgelopen;
- `WRONG_BRANCH` of detached/unknown branch;
- fetch-, ref- of probe-fouten.

Bij blokkade blijft de pending task staan en mag de executor geen lifecycle-
of repositorymutatie voor die task starten. Synchronisatie of herstel van de
Git-toestand gebeurt bewust buiten de executor; de worker lost een divergentie
nooit zelfstandig op.
