# Prediction Project Executor

Status: **operational capability-scoped Tier-A infrastructure**  
Build: `TIERA-PROJECT-EXECUTOR-20260929-E001`  
Formal qualification: `REQUIRES_HIGH_INTELLIGENCE_REVIEW`

Operational use for normal Prediction build/test/diagnose/user-level management work is enabled. The open qualification record is a governance status and does not block ordinary use inside the documented hard guardrails.

New sessions should first read `control/NEW_SESSION_LOCAL_EXECUTION.md` and `control/bridge_commands/CURRENT_STATE.md`.

## Doel

De project executor geeft ChatGPT voldoende lokale rechten om het Prediction-project te bouwen, testen en op user-level te beheren, zonder een onbeperkte root/shell-backdoor te maken.

De bestaande GitHub command bus blijft het transport. Voor daadwerkelijke code-uitvoering wordt het bestaande `DEV-` tunnelpad gebruikt, maar `project_task_executor.py` valideert een apart immutable task-spec uit deze repository en voert alleen expliciete capabilities uit.

## Harde grenzen

Altijd geblokkeerd:

- `sudo`, `su`, root/elevatie;
- live trading/order submission/order cancellation;
- wallet/crypto/fund movement;
- betaalde acties zonder specifieke voorafgaande goedkeuring via een daarvoor bedoeld pad;
- credential writes of toegang tot bekende credentialpaden;
- `git push`, remote-refmutaties, credential-Git en autonome GitHub-publicatie vanuit WSL;
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

1. ChatGPT schrijft via de GitHub connector een immutable spec naar `control/project_tasks/<TASK_ID>.json`.
2. Het spec bevriest `source_commit`, intelligence tier, model/reasoningregistratie, capabilities, operations en safetyflags.
3. De lokale executor haalt `bas1231/onderzoek` read-only op in een aparte mirror.
4. Voor repositorywerk maakt hij een geïsoleerde worktree/branch onder `~/.local/share/prediction-project-executor/worktrees/<TASK_ID>` vanaf exact `source_commit`.
5. Vóór uitvoering wordt duurzaam een lokale claim vastgelegd onder `~/.local/state/prediction-project-executor/`.
6. Child-Python krijgt een extra guard: writes alleen binnen worktree/temp, netwerk alleen loopback, beperkte subprocesses, geen remote Git.
7. Resultaten bevatten spec-hash, remote commit, source commit, worktree, branch, operations en exitstatus.
8. De lokale executor pusht nooit naar GitHub. Remote writes blijven via de expliciete ChatGPT GitHub-connector lopen.

## Task-authoring gotchas proven in A→Z repair (2026-10-08)

Use these exact task shapes to avoid pre-execution failures:

- Git operations require the single capability `local_git`; do not invent per-verb capabilities such as `git_status`, `git_diff`, `git_add` or `git_commit`.
- `python -c` is intentionally blocked. For inline repair logic, first create a repository-owned `.py` file with `write_text`, then execute that file with a `python` operation.
- For module execution, only the executor allowlist is valid. Use `python -m compileall` for compile checks; `py_compile` is not an allowlisted module.
- A `python -m pytest ...` or `python -m unittest ...` operation must have both capability `run_tests` **and** operation field `"test": true`. Without the per-operation flag the executor deliberately reports `run_tests capability required` even when the task capability list contains `run_tests`.
- Keep diagnostic/recovery tasks read-only whenever possible. A transport/result extraction failure does not justify changing bridge or executor code.

These rules are task-authoring constraints, not reasons to relax executor safety checks.

## Operation types

`write_text`: schrijft een bestand binnen de task-worktree; optioneel met verplichte preimage-SHA.

`delete`: verwijdert alleen één bestand binnen de worktree en vereist de exacte SHA-256 van de preimage.

`git`: alleen lokale allowlisted Git-subcommands zoals status/diff/add/commit/branch/switch; push/remote/credential operations zijn hard geblokkeerd.

`python`: repository-owned `.py` of allowlisted modules (`pytest`, `unittest`, `compileall`) onder de child guard. `python -m pytest ...` wordt fail-closed gerouteerd via de bestaande lokale provider `~/prediction_research/.venv/bin/python`; er wordt geen package-installatie, sudo of externe netwerktoegang toegevoegd.

`service`: `systemctl --user` op units die beginnen met `prediction-`.

`daemon_reload`: alleen `systemctl --user daemon-reload`.

`journal`: alleen user-journal van `prediction-*` units.

`install_runtime`: atomische installatie vanaf de worktree naar vooraf allowlisted Prediction runtimepaden of `~/.config/systemd/user/prediction-*` units.

## Transport via bestaande DEV tunnel

De receiver heeft al een asynchrone `DEV-` tunnel. Projecttaken gebruiken een klein manifest in `bas1231/fg-assistent/dev_tasks/<TASK_ID>.json` dat de canonical `project_task_executor.py` en guard synchroniseert en vervolgens `project_task_executor.py <TASK_ID>` start. De primaire command bus verstuurt hetzelfde task-ID via de huidige compatibility action `SIX_AI_HEALTH`.

Dit vermijdt een tweede lokale HTTP-executor en houdt één bestaande, bewezen wake/result-route. De exacte stap-voor-stap procedure staat in `control/NEW_SESSION_LOCAL_EXECUTION.md`.

## Bewezen operationele baseline

Live bewijs op 2026-09-29:

- `DEV-PRED-PROJECT-EXEC-INSTALL-E002` — compile + volledige deterministic unittest suite PASS;
- `DEV-PRED-PROJECT-EXEC-CANARY-E001` — isolated worktree, repository-owned Python write/execute en lokale Git-inspectie PASS;
- `DEV-PRED-PROJECT-EXEC-OPS-E003` — Python uitvoering, geïsoleerde lokale Git commit, bounded runtime install, `prediction-*` service status en journal read PASS.

Zie `control/bridge_commands/CURRENT_STATE.md` voor de nieuwste evidence.

## Governance

Muterende projecttaken blijven onder `methodology/AUTONOMOUS_BUILD_PROTOCOL.md` en, bij parallel werk, `methodology/PARALLEL_BUILD_PROTOCOL.md` vallen. Een capability is geen vrijbrief om objective, paden of acceptance criteria achteraf te verruimen.

Tier-A wijzigingen blijven formeel `REQUIRES_HIGH_INTELLIGENCE_REVIEW` totdat onafhankelijke Tier-A review, relevante deterministische tests en runtime-canary groen zijn. Die formele status mag niet worden voorgesteld als afgerond wanneer alleen functionaliteit is bewezen, maar blokkeert het normale operationele gebruik van de reeds bewezen executor niet.
