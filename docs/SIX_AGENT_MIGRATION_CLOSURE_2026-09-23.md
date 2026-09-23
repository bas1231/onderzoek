# Six-Agent Research-OS Migration Closure

Datum: 2026-09-23
Status: **MIGRATION_CLOSED — PRODUCTION RESEARCH ORCHESTRATION — NO_PROVEN_EDGE**

## Scope

Deze migratie vervangt de legacy hourly-role set door zes permanente Research-OS agents. De machineleesbare bron van waarheid blijft `agents/registry.json`.

Permanente agents:

1. `discovery` — capabilities `scout` + `recon_scout`;
2. `market_research` — capabilities `weather_twc` + `behavioral` + `informed_flow`;
3. `mechanics` — capabilities `settlement` + `microstructure`;
4. `algebra` — capability `algebra`;
5. `red_team_pentest` — capabilities `prebuild_killer` + `chief_falsifier`;
6. `research_director` — capability `research_director`.

`independent_reproducer` blijft uitsluitend een transient validation-role voor serieuze survivors en telt niet mee als permanente zevende agent.

## Afgeronde migratieblokken

### E001 — six-role exchange contract

De exchange-contractlaag accepteert en routeert de zes huidige agent-ID's; legacy role-ID's worden niet stil als huidige rollen behandeld.

Merge: `1949c3934f5c485ee3ba4a9077f29bca9b5a1eef`.

### E002 — immutable/create-once hourly AI bundle

Een `run_id` krijgt één create-once AI-work bundle en response-token. Een tweede Director-run binnen hetzelfde uur mag de bestaande bundle niet herschrijven of een nieuw token genereren.

Merge: `8d68dfaa23031a0654c628e0c43fd7724697e84b`.

### E003 — explicit validation-result response contract

`validation_results` gebruikt expliciet het huidige contract met verplichte `status` uit `PASS | FAIL | INCONCLUSIVE | WAITING` en toegestane validation modes. Het historische vrije `result`-veld is geen substituut voor `status`.

Merge: `88dae852b01373e3ea3b1819fc7ffa27844b6242`.

### Prospectieve end-to-end proof

Run `hourly-20260923T100000+0200` doorliep de volledige actuele keten:

`local Director -> immutable request -> ai/runtime-exchange -> scheduled AI worker -> exact six role_results -> response validation -> local ingest -> response receipt -> orchestration artifact`.

Geobserveerde runtime-gates:

- exact 6 work items;
- exact 6 role results;
- rollen: `discovery`, `market_research`, `mechanics`, `algebra`, `red_team_pentest`, `research_director`;
- `INVALID_VALIDATION_RESULTS: []`;
- local response aanwezig;
- local receipt aanwezig;
- orchestration artifact aanwezig;
- receipt-schema `PVA_AI_RESPONSE_RECEIPT_V1`;
- `live_trading=false`;
- `openai_api=false`;
- `paid_actions=false`;
- `wallet_actions=false`;
- expliciete operator-check: `E2E_6AI_RECEIPT_PASS`.

De remote worker-response is immutable aanwezig op `ai/runtime-exchange:ai_exchange/responses/hourly-20260923T100000+0200.json`.

### E004 — immutable historical-response quarantine

Twee pre-migration protocolfailures blijven als audit-evidence ongewijzigd op de exchange branch, maar vervuilen toekomstige gezonde ingest-status niet meer.

Quarantine is uitsluitend toegestaan bij een exacte combinatie van:

- bekend historisch exchange-pad;
- exact Git blob SHA;
- verwachte `ValidationError`-signature.

Iedere onbekende, gewijzigde of nieuwe failure blijft fail-closed in `errors`.

Bekende immutable artifacts:

- `hourly-20260922T150000+0200.json`, blob `95f6fa87c56604b71520d0cdc321f300c431f494`, pre-E001 legacy-role failure;
- `hourly-20260923T090000+0200.json`, blob `5e8c8f3e6899f1bafdfe6f9275fe7d144cc0e93b`, pre-E003 validation-result failure.

Dezelfde wijziging corrigeert `recovery_retry` telemetry: de vlag reflecteert nu of de response al bestond vóór receiver-executie en wordt niet meer automatisch `true` na iedere normale succesvolle apply.

PR: `#34`.
Merge: `aa839e5e8c8e7559908a2bf92065e5f2d9eb8d69`.
CI: `V14 validation` run `35836968810`, conclusion `success`.

## Closure criteria

De migratie is gesloten omdat alle migratie-specifieke gates zijn gehaald:

- zes permanente agent-ID's zijn canoniek en machineleesbaar;
- request- en response-contracten zijn onderling compatibel;
- same-hour bundle/token gedrag is idempotent/create-once;
- scheduled worker levert exact de gevraagde zesrollen-coverage;
- lokale receiver valideert en past een nieuwe six-role response toe;
- receipt en orchestration worden geproduceerd;
- historische incompatibele artifacts blijven immutable maar worden exact en zichtbaar gequarantained;
- nieuwe/onbekende protocolfouten blijven fail-closed;
- safety-invariants blijven uit voor trading, betaalde acties, walletacties en OpenAI API;
- target- en regression-CI voor E004 is groen.

## Operationele status na migratie

De Research-OS orchestration draait als productie-researchsysteem. Dit is **geen live trading-productie** en geen bewijs van een economische edge.

`NO_PROVEN_EDGE` blijft de juiste economische default totdat afzonderlijke signal-edge, market-edge en execution-realistische bewijs-gates zijn gehaald.

Een korte multi-cycle soak blijft nuttig als operationele efficiëntiemeting (duplicaten, latency, starvation, retries), maar is post-migration monitoring en geen open migratieblokker.
