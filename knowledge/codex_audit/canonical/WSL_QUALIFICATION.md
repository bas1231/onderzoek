> AFGEROND: gevraagde externe run20260925T095320Z-9b5ee7a3 ontvangen en beoordeeld. Niet opnieuw uitvoeren voor dit auditbesluit. Zie final_evidence_review/CLASSIFICATION.md.

# Kleinste veilige externe WSL-kwalificatie

Voer één opdracht in de normale WSL-terminal uit:

```bash
python3 ~/prediction_research_prod/knowledge/codex_audit/canonical/qualify_wsl.py
```

De scriptprint noemt een unieke map onder `knowledge/codex_audit/canonical/external_runs/`. Bewaar `RESULT.json`, `offline_contracts.log` en `real_loopback.log`; laat deze vervolgens beoordelen. Het script installeert niets, verandert geen Git-index en pusht niet.

## Wat dit daadwerkelijk toetst

| Onderdeel | Uitvoering | Bewijsgrens |
|---|---|---|
| Werkelijke sockets | Canonical ACK-server op vrije loopbackpoort, HTTP eerste/tweede ACK | Geen bestaande productie-outbox aangeraakt |
| Repaired router | Echte tijdelijke HTTP-handler: array400, routepersistency, conflicten409, corrupt route409 | Upstream opdrachtverwerking is een synthetische stub, geen echte commandreceiver |
| Herstart/herstel | Nieuwe module/listener met dezelfde tijdelijke routedirectory; replay blijft idempotent | Geen OS-/productieprocesrestart of reboot |
| Executor/queue | Bestaande canonical tests: echte subprocess-timeout, RESULT-hashes, terminale FAILED/policy-state | Tempdirectories; policy/Git/lifecycle externe preflights deels gemockt |
| Weather PIT | Recorders met vertraagde synthetische responses; receipt/config/chronology/coverage-invarianten | Geen nieuwe externe weatheropvraag, geen historische data herschreven |
| Agents/hourly | Offline canonical orchestratorchecks plus read-only systemd/laatste receipts/queueaantallen | Geen Director-aanroep, geen hourly jobstart, geen queuehervatting |
| Geïnstalleerde bridge | Uitsluitend localhost GET /health, veilige geselecteerde velden en diskhashvergelijking | Health/diskhash bewijst niet welke browsercode geladen is |
| Git | HEAD/status plus 22 geteste bronhashes | Commits bestaan al; geen mutatie nodig voor test |

Alleen tijdelijke testlisteners worden afgesloten en uitsluitend eigen TemporaryDirectory-data worden opgeruimd. Bestaande services worden niet gestart, gestopt, herstart, enabled of disabled. Geen /next, live POST/ACK/enqueue, browserbericht, order, wallet, betaald netwerk of externe API. De bestaande lokale token wordt alleen in het geheugen gebruikt voor localhost-authenticatie, niet opgeslagen of geprint; geen redirects.

## Interpretatie

De Codex-self-test staat expliciet als CODEX_SANDBOX_SELF_TEST_NOT_EXTERNAL_QUALIFICATION gemarkeerd: 128 offline tests pass, sockets/systemd geblokkeerd. Dat is niet het ontbrekende externe WSL-bewijs.

Een succesvolle externe run kan de **tijdelijke echte sockets en restartpersistency** kwalificeren. Hij kan deployed drift, actuele intervaloverride en stale hourly-receipts aantonen. Hij geeft bewust nooit automatisch productie-E2E-PASS.

Nog niet veilig automatisch uitvoerbaar in deze stap: daadwerkelijk browserbericht naar Director, productie-restart/reboot en nieuwe hourly-run. Die kunnen bestaande research/bridgeverwerking activeren of botsen met ownerwerk/legacy deployment. Als receipts stale/blocked zijn of diskhashes afwijken, blijven die onderdelen UNPROVEN; geen automatic restart of deployment. Na ontvangst van de WSL-evidence kan een eventuele gerichte canary op de dan feitelijk aangetroffen toestand worden ontworpen.

Het script kan exit1 geven bij falende tests, maar schrijft het resultaat eerst weg. Een ontbrekende venv/afwijkende repairhash geeft exit2 en een expliciet preflightrecord. Geen betaalde of installatie-fallback. Exit0 betekent alleen dat de afgebakende testgroepen slaagden, niet dat alle echte runtimecomponenten gekwalificeerd zijn.
