# Residuele risico's na canonical herstel

- Geen nieuwe canonical commit binnen read-only .git; exact diff/manifest en getest lokaal commitplan beschikbaar.
- Huidige hourly/sync blokkeert op ownerwerk/divergentie; onderzoek niet zelfstandig hervat.
- Bestaande processen/browser/legacycheckout gebruiken niet aantoonbaar de gewijzigde bron. Geen automatische restart/deploy verricht.
- Socket/systemd/browser/reboot-E2E blijft BLOCKED/UNPROVEN. Socketloze ACK/terminalisatie is begrensde integratie-evidence.
- 15s fast-deadman versus owner600s inactivity is onbeslist. Staged installer ongewijzigd, test intact rood.
- Historische responseklokken niet herstelbaar door codewijziging; onbekende manifests uitgesloten.
- TWC-final 1–4h target, volledige PIT, untouched holdout, signal-edge en market-edge UNPROVEN/NO_PROVEN_EDGE.
- Lexicale policy is geen volledige sandbox; Node DOM is geen bewijs voor alle echte browser-/multitab-/virtualisatiegevallen. Nieuwe scoped cache vereist deploymentcanary.
- Volledige crash/reboot/concurrencyrecovery is niet bewezen. Historische failure-evidence blijft behouden.

Geen resterend risico is stilzwijgend geaccepteerd als volledige audit-PASS.
