# Resterende risico's en blokkades

- HIGH correctnessbevindingen zijn bevestigd en niet gerepareerd; geen audit-PASS.
- .git read-only verhindert alle canonical commits, worktree/lease en baselinevoorwaarde voor reparaties. Workspacebestanden overleven deze sessie maar zijn **niet** duurzaam in Git vastgelegd.
- Systemd-userbus/sockets ontoegankelijk; geen echte browserroundtrip, reboot-, logout-, crash- of productierestarttest. Geen uitspraak dat actieve processen momenteel gezond zijn.
- Geïnstalleerde scripts/legacy checkout verschillen van canonical bron. Browsergeladen versie onbekend.
- 1–4 uur final-TWC predictor, sterke vijfvoudige baselines, CRPS/Brier/logloss/calibration en untouched holdout zijn niet aangetoond in de getraceerde lane. Andere private bronrepo's niet volledig geaudit.
- Historische data kunnen niet door reparatie van recorderklokken met terugwerkende kracht exact PIT worden. Nieuwe prospectieve evidence is nodig voor claims op secondenniveau.
- Securityscan beperkte zich tot high-confidence patronen in huidige getrackte werkboom; geen volledige geschiedenis/entropy- of credentialaudit. Twee PEM-headerhits zijn detectieliterals, geen aangetroffen sleutelmaterialen. Geen bewijs van secrets gevonden binnen deze beperkte scan; geen algemene clean-claim.
- Lokale Git-fixtures van bestaande tests pushen uitsluitend naar tijdelijke lokale bare repositories. Geen productie- of netwerkremote is gepusht.
- Tweede review is een nieuwe adversariële ronde door dezelfde auditor, geen onafhankelijke tweede persoon/model. Onafhankelijke assurance blijft beperkt.
- Alle brede éénmalige jobs onder control/jobs zijn niet blind uitgevoerd: sommige schrijven services of gebruiken echte data/netwerk. Testscope wordt niet gelijkgesteld aan de hele repository.

## Hervatting na baseline 80a5ff7

Baseline door eigenaar veilig gecommit en geverifieerd. Vervolgcommits/coordinator blijven read-only. Productiebronhashes ongewijzigd. Voorstellen, exacte commands en resultaten: `remediation/`. Nieuwe bevindingen AUD-CODEX-015 t/m 018; geen productiefix geclaimd. Nieuwe gedragstests: 52 passed. Breedste huidige regressie: 444 passed, 8 failed (broad_v3). De oorspronkelijke negen invarianten slagen in de voorstelkopie; oorspronkelijke rode evidence blijft bewaard.

## Actuele hervattingsstatus — 25 september 2026

Baseline 80a5ff7 is geverifieerd en veilig. Oudere tekst over ontbrekende baselinecommit is historisch; vervolgcommits/lease blijven geblokkeerd door read-only .git. Productie ongewijzigd. Zie FINAL_AUDIT_REPORT.md en remediation/TRIAGE.md: 20 bevindingen, 64 auditchecks geslaagd op voorstelbron; brede suite en duurzame replay beide 447 passed / 8 failed. Geen productie-FIXED/RETESTED. Frozen acceptancecriteria zijn niet versoepeld. Exact vervolg staat in CONTINUATION.
