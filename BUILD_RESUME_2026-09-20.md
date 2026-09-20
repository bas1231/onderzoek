# Build Resume — 2026-09-20

Status: **ACTIVE**

De eigenaar heeft op 2026-09-20 om 07:36 CEST expliciet opgedragen: `ga verder met de build`.

Deze instructie hervat research- en control-plane-builds en supersedeert voor die scope `BUILD_FREEZE_2026-09-19.md`.

## Harde grenzen blijven ongewijzigd

- geen live trading;
- geen orders;
- geen wallet- of fund-movement-acties;
- geen betaalde acties zonder voorafgaande expliciete toestemming;
- geen automatische promotie van `NO_PROVEN_EDGE` naar een economische claim;
- candidate-specifieke builds moeten voortaan door de pre-build warrant gate.

## Eerste hervatte bouwstap

`EHB-001 — Pre-build warrant`

Doel: nieuwe candidate-builds fail-closed blokkeren tenzij minimaal de mechanisme- en pre-build-killer-gates aantoonbaar PASS zijn, de candidate voldoende ver in de lifecycle staat en de aangevraagde capabilities geen verboden live/kosten/execution-functionaliteit bevatten.

De machineleesbare actuele buildstatus staat in `control/BUILD_STATE.json`.
