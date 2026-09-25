# Definitieve beoordeling van externe WSL-evidence

Bron: `canonical/external_runs/20260925T095320Z-9b5ee7a3/RESULT.json`, `offline_contracts.log`, `real_loopback.log`. Alle drie volledig gelezen; hashes vastgelegd in REVIEW.json. De eigenaar bevestigt de externe herkomst. De generieke LOCAL_INVOCATION_UNATTESTED-runnerlabel is geen mislukte test.

| Observatie | Classificatie | Betekenis / besluit |
|---|---|---|
| 128 offline tests, exit0 | Gekwalificeerde afgebakende broncontracten | Bevestigt bestaande canonical fixes; overlap met eerdere475, niet optellen tot607 unieke tests. |
| 4 echte loopbacktests, exit0 | Werkelijk uitgevoerde socket-/fixture-integratie | Eerste/herhaalde ACK, malformed envelope, routeconflict/corruptie en persistente rebind groen. Upstream blijft synthetisch. |
| Eerdere socket-PermissionError nu verdwenen | Omgevingsbeperking, extern opgeheven | De oorspronkelijke ene suitefailure slaagt in WSL; geen productiecodefix nodig. Niet beweren dat een nieuwe volledige476-test-run is uitgevoerd. |
| Slottekst “Geen productie-E2E-PASS...” | Verwachte kwalificatiebeperking, geen runnerdefect | De runner drukt deze tekst bewust altijd af: testscope bevat geen live browser-/Director-/rebootcyclus. RESULT.runtime_e2e is vooraf UNPROVEN. Een reviewer moet bewijs beoordelen. |
| Deployed router +3weatherbestanden matchen exact oude vóór-reparatiehashes | Bevestigde operationele deploymentgap, AUD-013 | Dit zijn nog ongerepareerde deployed artifacts. Canonical fixes bestaan al; opnieuw canonical wijzigen lost kopieën niet op. Paden buiten toegestane writable workspace; geen install/restart/sandboxuitbreiding. |
| Installed userscript wijkt af | Deploymentdrift / residueel risico | Verschil alleen bewijst niet dat alle oude fouten aanwezig zijn. Werkelijk in browser geladen versie blijft onbekend. |
| /health op8765/8767: HTTP200, ok=true | Werkelijke lokale bereikbaarheid, beperkte health-evidence | Geen attestatie van loaded bron of nuttige downstream-uitvoering; heft deployed hashverschillen niet op. |
| Hourly-director service failed; timer active/waiting | Operationele keten niet gekwalificeerd, AUD-002 | Timerstatus bewijst geen research. Laatste completed receipt circa19,82uur oud. Exacte systemd-failureoorzaak niet uit ActiveState/ExecMainStatus alleen afleiden. |
| Prod-sync BLOCKED; checkpoint FAIL_CLOSED | Verwachte safety-refusal én operationele blokkade | Receipt meldt niet-lege index; ownerwerk bestaat aantoonbaar. Guard behouden, geen reset/auto-commit/push of geforceerde queuehervatting. |
| Executor active, NRestarts1293 | Historische restartteller / residueel risico | Eén meting bewijst geen huidige crashloop. Geen oorzakelijke claim dat deze1293 restarts na herstel plaatsvonden. Nieuwe processtart of active zegt niet dat taken nuttig verwerkt worden. |
| Queue: pending28, running0, completed367, failed92 | Voorraadmeting | Geen orphan in deze running-snapshot, maar geen bewijs dat een nieuwe echte taak succesvol door de keten ging. |
| Weather oneshot services inactive/dead, status0 | Niet op zichzelf een defect | Zonder timer/triggertijd geen conclusie dat collectoren kapot zijn. Wel bevestigde oude deployed weatherbron. |
| Heartbeatinterval ontbreekt in geselecteerde healthvelden | Onbewezen actieve override | Runner laat null weg; niet interpreteren als15s of600s. Defaultbronbeleid600s blijft onderbouwd door ownerintent/tests. |

## Eindbesluit

**Software: AUDIT_INCOMPLETE + RESIDUAL_RISK.** Afgebakende bron- en tijdelijke sockettests zijn goedgekeurd, globale productie-E2E niet. Dat oordeel volgt uit operationele deploymentdrift en ontbrekende actuele ketenevidence, **niet** uit NO_PROVEN_EDGE.

**Wetenschap/trading: NO_PROVEN_EDGE**, afzonderlijk; geen claim van winstgevendheid nodig om correcte software te bouwen.

Geen nieuwe canonical productiebug en geen kwalificatietestbug aangetroffen in deze externe run. Geen nieuwe externe test nodig om dit eindbesluit te nemen. Nogmaals hetzelfde script draaien kan onuitgerolde reparaties niet oplossen. Eventuele deployment en gecontroleerde echte ketencanary is een afzonderlijk werkpakket met behoud van ownerwerk en toegestane grenzen.
