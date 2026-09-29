# Prediction Project Executor

Status: **provisional Tier-A infrastructure**  
Build: `TIERA-PROJECT-EXECUTOR-20260929-E001`  
Qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

## Doel

De project executor geeft ChatGPT voldoende lokale rechten om het Prediction-project te bouwen, testen en op user-level te beheren, zonder een onbeperkte root/shell-backdoor te maken.

De bestaande GitHub command bus blijft het transport. Voor daadwerkelijke code-uitvoering wordt het bestaande `DEV-` tunnelpad gebruikt, maar de nieuwe `project_task_executor.py` valideert een apart immutable task-spec uit deze repository en voert alleen expliciete capabilities uit.

## Harde grenzen

Altijd geblokkeerd:

- `sudo`, `su`, root/elevatie;
- live trading/order submission/order cancellation;
- wallet/crypto/fund movement;
- betaalde acties;
- credential writes of toegang tot bekende credentialpaden;
- `git push`, remote-refmutaties, credential-Git en autonome GitHub-publicatie;
- willekeurige externe netwerkverbindingen vanuit projectcode;
- `shell=True` en onbeperkte shellcommando's;
- niet-Prediction systemd user-units;
- writes buiten een taakworktree, taak-temp of expliciet allowlisted Prediction-runtimepad.

Deze grenzen blijven gelden ongeacht een brede gebruikersopdracht om het project te beheren.

## Capabilities

Een `PREDICTION_PROJECT_TASK_V1` vraagt alleen wat de taak nodig heeft:

- `read_repository`
- `write_worktree`
- `run_project_python`
- `run_tests`
- `local_git`
- `read_runtime`
- `write_runtime`
- `user_service_manage`
- `read_logs`

Elke task bevat daarnaast verplicht `live_trading:false`, `paid_actions:false`, `wallet_actions:false`, `remote_git_write:false` en `credential_write:false`.

## Uitvoeringsmodel

1. ChatGPT schrijft een immutable spec naar `control/project_tasks/<TASK_ID>.json`.
2. Het spec bevriest `source_commit`, intelligence tier, model/reasoningregistratie, capabilities, operations en safetyflags.
3. De lokale executor haalt `bas1231/onderzoek` read-only op in een aparte mirror.
4. Voor repositorywerk maakt hij een geïsoleerde worktree/branch onder `~/.local/share/prediction-project-executor/worktrees/<TASK_ID>` vanaf exact `source_commit`.
5. Vóór uitvoering wordt duurzaam een lokale claim vastgelegd onder `~/.local/state/prediction-project-executor/`.
6. Child-Python krijgt een extra guard: writes alleen binnen worktree/temp, netwerk alleen loopback, beperkte subprocesses, geen remote Git.
7. Resultaten bevatten spec-hash, remote commit, source commit, worktree, branch, operations en exitstatus.
8. De lokale executor pusht nooit naar GitHub. Remote writes blijven via de expliciete ChatGPT GitHub-connector lopen.

## Operation types

`write_text`: schrijft een bestand binnen de task-worktree; optioneel met verplichte preimage-SHA.

`delete`: verwijdert alleen één bestand binnen de worktree en vereist de exacte SHA-256 van de preimage.

`git`: alleen lokale allowlisted Git-subcommands zoals status/diff/add/commit/branch/switch; push/remote/credential operations zijn hard geblokkeerd.

`python`: repository-owned `.py` of allowlisted modules (`pytest`, `unittest`, `compileall`) onder de child guard.

`service`: `systemctl --user` op units die beginnen met `prediction-`.

`daemon_reload`: alleen `systemctl --user daemon-reload`.

`journal`: alleen user-journal van `prediction-*` units.

`install_runtime`: atomische installatie vanaf de worktree naar vooraf allowlisted Prediction runtimepaden of `~/.config/systemd/user/prediction-*` units.

## Transport via bestaande DEV tunnel

De receiver heeft al een asynchrone `DEV-` tunnel. Nieuwe projecttaken gebruiken een klein manifest in `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` dat de canonical `project_task_executor.py` en guard synchroniseert en vervolgens `project_task_executor.py <TASK_ID>` start. De primaire command bus verstuurt hetzelfde task-ID via action `SIX_AI_HEALTH`.

Dit vermijdt een tweede lokale HTTP-executor en houdt één bestaande, bewezen wake/result-route.

## Governance

Muterende projecttaken blijven onder `methodology/AUTONOMOUS_BUILD_PROTOCOL.md` en, bij parallel werk, `methodology/PARALLEL_BUILD_PROTOCOL.md` vallen. Een capability is geen vrijbrief om objective, paden of acceptance criteria achteraf te verruimen.

Tier-A wijzigingen blijven `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat onafhankelijke Tier-A review, relevante deterministische tests en runtime-canary groen zijn.
