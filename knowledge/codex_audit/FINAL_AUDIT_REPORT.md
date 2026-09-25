# Final qualification — 25 september 2026

## 1. Actuele kwalificatie

**SOFTWARE: AUDIT_INCOMPLETE + RESIDUAL_RISK.** Canonical bronreparaties zijn FIXED_AND_RETESTED en externe sockettests slagen. Globale productie-E2E voldoet niet aan de acceptatiecriteria wegens bevestigde deploymentdrift en een niet-aangetoonde actuele hourlyketen.

**WETENSCHAP/TRADING: NO_PROVEN_EDGE**, afzonderlijk. Dit is geen softwarefailure en is niet de reden om software-PASS te weigeren.

## 2. Executive summary

Zes lokale commits geverifieerd; alle 22 gerepareerde bron-/testhashes matchen zowel HEAD als de eerder geteste werkboom. De definitieve beschikbare suite telt **475 passed / 1 failed**. De enige lokale failure was socketaanmaak in de sandbox; die exacte test slaagt nu extern. Beide gevraagde WSL-groepen slagen: **128 offline en 4 echte loopbacktests**. De oorspronkelijke globale suite is niet opnieuw integraal in WSL uitgevoerd. Het timingconflict is voor het bedoelde bronbeleid opgelost zonder installer- of indexwijziging. Wetenschappelijke edge blijft onbewezen.

## 3. Exacte scope

Uitsluitend finale kwalificatie: commit/hashverificatie, historische policyreconciliatie, gerichte/brede regressie en een veilige externe WSL-runner. Geen reparaties opnieuw uitgevoerd, geen nieuwe brede audit, geen deploy/serviceactivatie/queuehervatting, geen push of betaalde/financiële actie. Eerdere volledige audit staat in commit 538c20c en FINDINGS.jsonl.

## 4. Architectuur

SYSTEM_MAP.md blijft de bronkaart: timer/sync → hourly/Directoruitwisseling → agentpackets/evidence → executor/persistence → bridge/browser. Zes domeinrollen zijn geen bewijs van zes zelfstandige modelprocessen. Prod en legacy weathercheckout en geïnstalleerde bridges kunnen verschillende code laden.

## 5. Tests

- Voorafgaande canonical regressie: 474 pass/2 fail.
- Policyreconciliatie, focused: 5 pass/11 deselected.
- Finale brede canonical regressie: 475 pass/1 socket-PermissionError, exit1.
- WSL-scriptselftest binnen Codex: 128 offline pass; echte loopbackgroep 2 pass/2 geblokkeerd; systemd geblokkeerd.

Exacte commands/tijden/omgeving: remediation/qualification_policy.*, qualification_final_regression.*. De selftest staat onder canonical/external_runs/ expliciet gemarkeerd als CODEX_SANDBOX_SELF_TEST_NOT_EXTERNAL_QUALIFICATION. Geen externe kwalificatie gefingeerd.

## 6. Runtime-evidence

Externe run `20260925T095320Z-9b5ee7a3` volledig beoordeeld: RESULT.json en beide testlogs. Werkelijke loopback/ACK/routing en module/listener-rebind slagen. Systemd is toegankelijk; beide lokale healthendpoints geven HTTP200. Dit heft de eerdere omgevingsbeperking op.

Het externe bewijs toont tegelijk concrete blockers: installed router en drie weatherbestanden matchen exact de vóór-reparatiehashes; installed userscript wijkt ook af. Hourly-director staat failed, timer active/waiting; laatste completed receipt is circa 19,82uur oud. Prod-sync is BLOCKED. Het corresponderende lokale receipt noemt expliciet een niet-lege index; dat is een verwachte safety-refusal. Geen guard omzeild.

Executor active met NRestarts=1293 is één historische teller, geen bewezen huidige crashloop. running=0/pending=28 is een voorraadmeting, geen nieuwe nuttige ketenuitvoering. Inactive/dead oneshot weatherunits zijn op zichzelf geen defect. De exacte servicefailureoorzaak en loaded browserversie zijn niet uit deze snapshot bewezen.

## 7. Bevindingen

23 permanente bevindingen: 17 FIXED_AND_RETESTED, 2 CONFIRMED_OPEN, 1 BLOCKED, 2 RESIDUAL_RISK, 1 UNPROVEN. Exacte severity, reproducties en commitkoppelingen staan in FINDINGS.jsonl en OPEN_FINDINGS.md. Nummer 017 betreft een vóór integratie ontdekte voorstelregressie, niet een afzonderlijk productie-incident.

## 8. Gerepareerd en gecommit

Weatherreceipt/PIT/coverage/targetchronologie; fail-closed economics; route/envelope/upstreamfouten; timeout/policy/queue-terminalisatie; composerbehoud, zichtbaar leveringsbewijs en dedupe/backoff. Alle relevante bronhashes matchen het eerder geteste resultaat. Herstelcommits zijn nu in ieder betrokken findingrecord ingevuld. Dat bewijst nog geen geladen runtimeversie.

## 9. Resterende software-/testbeperkingen

De TCP-ACK-test bleef in Codex rood door PermissionError en slaagt nu ongewijzigd extern. Geen productie- of testfix nodig voor deze eerdere failure. De voormalige 15s-installercheck is inhoudelijk gereconcilieerd, niet simpelweg verwijderd: gegenereerde runtime wordt op 599s/600s en nieuwe activiteit getest, inclusief nonce/fresh-task/done/reset-guards. Geen skip/xfail toegevoegd.

## 10. Timingbeleid — besluit

ffc3ebf introduceerde 600s inactivity; 41ee276 liet de installer later 15s genereren; 0d87745 testte dat terecht. Het **expliciete staged ownerwerk** draait die 15s-transformatie vervolgens terug naar 600s, behoudt nonce/fresh-task-hardening en eist activity-resetguards. Daarom is **600s volledige inactivity de huidige bedoelde default voor deze werkboom**. Geen arbitraire auditor-keuze en geen installerwijziging.

HEAD van de installer bevat nog de oudere versie; het bedoelde ownerwerk blijft staged. Ook een actieve mode kan een expliciete 15–600s-override bevatten. Het WSL-script leest die waarde; het verandert hem niet. Er is geen open menselijke keuze over de staged default. Mocht een 15s-runtimeoverride worden aangetroffen, moet de eigenaar vóór wijziging bevestigen of die bewust behouden moet blijven. Zie canonical/final_qualification/POLICY_DECISION.md.

## 11. Residuele risico's

Deploymentdrift, daadwerkelijk geladen browsercode, productiecrash/reboot/herstel en actuele volledige hourly-keten blijven onbewezen. Diskhash en HTTPhealth zijn geen loaded-code- of E2E-attestatie. Lexicale policy is geen volledige securitysandbox. Geen van deze risico's is als algemene PASS geaccepteerd.

## 12. Weather/TWC

Finale TWC settlement 1–4 uur probabilistisch voorspellen is niet gekwalificeerd. KWI-minute publication-lag is een ander doel. Interne TWC-werking niet aangenomen. Vergelijkbare OOS persistence/trend/METAR/NWP/WeatherRunner en volledige probabilistische metrics zijn niet aangetoond.

## 13. Point-in-time

Bevestigde lokale receipt/config/chronologydefecten gerepareerd en hergetest. Onbekende oude responseklokken niet gereconstrueerd; legacy manifests fail-closed uitgesloten. Volledige PIT over alle forecast/revisie/feature/settlementpaden blijft UNPROVEN.

## 14. Holdout

UNPROVEN; geen gegarandeerd untouched holdout/toegangsgeschiedenis aangetoond. Geen tuning, herlabeling of wijziging van raw/immutable evidence. Gedeelde settlementbuckets en station×local_date-afhankelijkheid niet als onafhankelijke trials behandeld.

## 15. Signal edge

NO_PROVEN_EDGE / UNPROVEN voor het gevraagde finale target. Bronherstel of technische gates bewijzen geen signaalvoordeel.

## 16. Market edge

NO_PROVEN_EDGE. Geen volledige executable-price/L2/quantity/fee/fill/slippage/latency/finalityonderbouwing. Geen live of testorders geplaatst.

## 17. Bridge

Canonical contracts en echte tijdelijke sockets, routepersistency en herladen listener zijn extern groen. De runner heeft alleen deployed GET /health en hashes gelezen, geen productiebericht/opdracht verstuurd. Werkelijke browser/Director-E2E blijft UNPROVEN; de deployed router matcht de oude defecte bron.

## 18. Agents/hourly

Bestaande historische traces en offline orchestratorchecks blijven begrensde evidence. De externe run heeft systemdstatus, queueaantallen en receipts verzameld; hourly failed/stale en sync BLOCKED zijn daarmee opnieuw bevestigd. Het start geen nieuw onderzoek en roept geen modellen aan. Stale/blocked receipts mogen geen hourly-PASS worden.

## 19. Regressieresultaat

Vorige brede canonical run: 476 tests, 475 pass en één sandbox-socketfailure. Extern: 128 offline en 4 sockettests pass, inclusief de oorspronkelijke socketfailure plus de aanvullende routertest. Die suites overlappen; geen nieuwe volledige 476/476-run geclaimd. Alle 22 geteste repairhashes zijn opnieuw bevestigd. Ownerinstaller/index bleven behouden.

## 20. Adversariële review

Eerdere canonical red/green-falsificaties blijven bewaard: false delivery, replay/backoff, raw upstreamtimeout, economics-overflow, receipt/batchvolgorde. In deze final-onlyfase geen nieuwe brede audit gestart. Policyreconciliatie behoudt echte grens- en identityguards.

## 21. Finale bewijsgrens

Semantiek/provenance: commits, sourcehashes en ownerpolicy geverifieerd. Reproduceerbaarheid: focused/brede canonical tests plus duurzaam extern script. Economie/execution: onvoldoende bewijs, dus geen promotie. Actieve service, geldige healthresponse en groene fixture zijn geen volledige E2E-PASS.

## 22. Definitief besluit en lokale vastlegging

**Geen nieuwe externe test nodig voor dit oordeel.** De runner is niet defect: de slottekst “Geen productie-E2E-PASS” is bewust onvoorwaardelijk omdat zijn scope geen volledige live keten bevat. Alle uitgevoerde tests slaagden. De concrete deploymentgap en stale/failed hourly verhinderen een globale PASS; nogmaals dezelfde tests draaien kan die niet oplossen.

Er is geen nieuwe veilig in canonical bron te repareren bug aangetoond. De betreffende bronfixes bestaan al. De nog oude deployed paden liggen buiten de writable workspace; ze zijn niet overschreven en services zijn niet blind herstart. Opvolgwerk is gecontroleerde ownerintegratie/deployment en vervolgens echte loaded-version/ketencanary. Dat is een afzonderlijk operationeel werkpakket, niet een laatste test die hier een PASS kan opleveren.

Leg uitsluitend de definitieve auditstate lokaal vast; niets pushen:

```bash
(
  cd ~/prediction_research_prod &&
  git add -- knowledge/codex_audit &&
  git commit --only -m "audit: finalize external WSL qualification" -- knowledge/codex_audit
)
```

De overige staged ownerbestanden blijven buiten deze commit. De gereconcilieerde timingtest is een nog afzonderlijke wijziging buiten de auditmap en hangt samen met het behouden staged 600s-installerwerk; beide horen later bewust samen te worden beoordeeld/gecommit. Dit eindrapport committeert dat ownerwerk niet stilzwijgend. De zes bestaande repaircommits zijn intact; de oude commit_locally.py niet opnieuw uitvoeren.

## 23. Commit- en evidencereferenties

- e6e0f73: regressiecontracts.
- 3206ec1: weather/PIT.
- 2b5e137: proof-gate.
- 28d3e10: executor/policy.
- b1766ed: consumer-routing/delivery.
- 538c20c: auditcheckpoint.

Baseline 80a5ff7 en voorstelcheckpoint db6c0f3 intact. canonical/final_qualification/verification.json verifieert commits, paden en geteste hashes. POLICY_DECISION.md en preservation_and_commit.json onderbouwen policy/ownerbehoud. qualification_*.json/log bevatten regressie. Nieuwe kwalificatiedocumenten, script en timingtest zijn nog niet gecommit: actuele stagingprobe blijft read-only. Bestaande zes commits zijn volledig behouden; niets gepusht.

## 24. Exacte externe evidence-review en classificatie

`canonical/external_runs/20260925T095320Z-9b5ee7a3/{RESULT.json,offline_contracts.log,real_loopback.log}` is ongewijzigd bewaard. `canonical/final_evidence_review/REVIEW.json` legt hashes, sourcevergelijking en besluit vast. `CLASSIFICATION.md` onderscheidt productie-deploymentgap, runner/testgedrag, opgeheven omgevingslimiet, verwachte safety-refusal en residuele onzekerheden. Alle 17 FIXED_AND_RETESTED blijven op canonical bron van toepassing; AUD-013 is nu HIGH CONFIRMED_OPEN deploymentgap, niet een teruggedraaide bronfix.

De echte externe herkomst is door de eigenaar bevestigd. Het generieke runnerlabel LOCAL_INVOCATION_UNATTESTED doet de gemeten resultaten niet teniet. Healthinterval ontbreekt in de geselecteerde output; de runner filtert null weg, dus dit is geen bewijs voor een actieve 15s- of 600s-override. Het bedoelde 600s-bronbeleid is ongewijzigd.
