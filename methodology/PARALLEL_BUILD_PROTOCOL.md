# Parallel Build Protocol V1

Status: **NORMATIVE** voor iedere muterende build wanneer meer dan één AI-sessie/builder aan deze repository kan werken.

Doel: 2–3 builders mogen tegelijk nuttig werk doen zonder elkaars wijzigingen, Git-history of validatie te beschadigen.

## 1. Kernregels

1. Iedere muterende sessie registreert vóór implementatie een unieke `session_id`, `task_id`, broncommit, branch/worktree en `planned_paths` via `control/jobs/parallel_build_coordination.py`.
2. Iedere muterende sessie controleert vóór schrijven welke andere actieve sessies bestaan.
3. Twee muterende sessies mogen **nooit dezelfde worktree** delen. Een tweede muterende sessie in dezelfde worktree wordt fail-closed geblokkeerd.
4. Ook in verschillende worktrees worden overlappende `planned_paths` fail-closed geblokkeerd. Prefix-overlap telt mee: `control/foo` conflicteert met `control/foo/bar.py`.
5. Iedere builder gebruikt een eigen branch/worktree voor muterende code. `main` is integratiegrond, niet de gezamenlijke edit-worktree.
6. Read-only research mag parallel blijven lopen zolang zij geen repositorymutaties uitvoert.
7. Een sessie vernieuwt haar lease regelmatig. Verlopen leases blokkeren nieuwe sessies niet; stale runtime-state wordt nooit als geldige ownership behandeld.
8. Conflicten worden niet automatisch semantisch opgelost. Bij overlap is de uitkomst `BLOCKED_*` totdat de scope of integratie expliciet is herzien.

## 2. Integratie naar main

1. Slechts één sessie tegelijk mag de integration lock bezitten.
2. Vóór merge/publish wordt `origin/main` opnieuw opgehaald.
3. Als `origin/main` sinds de `source_commit` is veranderd, worden alle gewijzigde paden vergeleken met de eigen `planned_paths`.
4. Overlap met nieuwe main-wijzigingen geeft `BLOCKED_OVERLAPPING_MAIN_CHANGE`.
5. Geen overlap betekent nog niet automatisch publiceren: de sessie moet de actuele `origin/main` incorporeren en de relevante acceptance/regression-tests opnieuw uitvoeren.
6. Pas daarna mag de sessie de actuele main-SHA als gevalideerd markeren.
7. Publish is alleen toegestaan wanneer:
   - de sessie de integration lock bezit;
   - `last_validated_main == current origin/main`;
   - de eigen HEAD gebaseerd is op de actuele `origin/main`;
   - de tracked worktree clean is;
   - bestaande build-governance en acceptance criteria nog steeds PASS zijn.
8. Geen force push, reset of history rewrite om concurrencyproblemen te verbergen.
9. Na integratie wordt de integration lock vrijgegeven en de sessielease beëindigd.

## 3. Runtime state

Lokale coordination-state staat onder:

`/.runtime/build_coordination/`

Deze state is niet canonical en wordt niet gecommit. Git blijft de permanente audit trail.

Per actieve sessie wordt minimaal vastgelegd:
- `session_id`;
- `task_id`;
- mutating/read-only;
- `planned_paths`;
- branch;
- `source_commit`;
- worktree;
- host;
- heartbeat/expiry;
- status;
- `last_validated_main`.

De integration lock heeft één eigenaar en een korte TTL zodat een crash geen permanente deadlock maakt.

## 4. Verplichte volgorde voor muterende sessies

`status -> start lease -> build/test -> acquire integration -> premerge -> sync/revalidate -> mark-validated -> publish-check -> merge/publish -> release integration -> finish lease`

Voorbeeldstatus:

```text
ACTIVE BUILDERS: 2
A scheduler  worktree-A  control/scheduler/**
B heartbeat  worktree-B  control/nightshift/**
PATH CONFLICT: none
PARALLEL BUILD: allowed
```

Als twee sessies dezelfde worktree of overlappende paden claimen:

```text
BLOCKED_PARALLEL_CONFLICT
```

## 5. Scopegrens

Deze coördinatielaag is repository/WSL-side. Zij vereist geen wijziging aan de browser-extensie of bridge-transportcode. De bestaande bridge mag de coordinator als gewone repository-owned Python-job aanroepen.

Kosten, live trading, wallets, credentials en andere afzonderlijk goedkeuringsplichtige acties blijven volledig onder de bestaande safety/governance-regels vallen.
