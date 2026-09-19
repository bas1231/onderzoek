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
