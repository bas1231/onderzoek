# Timingbeleid: bewijsbesluit

1. `ffc3ebf` (2026-09-24 07:42 +02:00) introduceerde tien minuten inactivity in bridge_server_hardened.py; die canonical bron heeft nog DEFAULT_HEARTBEAT_INTERVAL=600.
2. `41ee276` (14:01 +02:00) liet de installer die bron naar 15s patchen. `0d87745` voegde de exacte 15s-test toe. De test was dus toen terecht, geen historische false positive.
3. Het bewaarde staged ownerwerk in install_hardened_bridge.py verwijdert die 15s-transformatie **expliciet**, noemt het behoud van tien minuten, gebruikt HEARTBEAT_IDLE_SECONDS=600 en eist tegelijk nonce/fresh-task/done/activity-reset guards. Dit is coherent beoogd bronbeleid, geen door de auditor gekozen getal.
4. De eigenaar vraagt dat staged timingwerk te behouden. Installer en index zijn byte-equivalent gebleven tijdens deze kwalificatie.

## Besluit

**Huidige bedoelde default voor deze werkboom: 600s volledige inactivity.** De oude 15s-literaltest is vervangen door gedragstests van de gegenereerde runtime: geen event op 599s, wel op 600s; recente activiteit stelt het interval opnieuw uit; nonce/fresh-task en done/reset-guards blijven vereist; patchgeneratie is idempotent.

Er is geen menselijke keuze nodig om deze stale defaulttest te reconciliëren. Wel blijven twee verschillende toestanden zichtbaar: de bedoelde installer is nog staged ownerwerk, terwijl HEAD voor dat bestand de eerdere 15s-installer bevat; een al geïnstalleerde runtime kan dus nog anders zijn. De auditor committeert/overschrijft dat ownerwerk niet automatisch.

De runtime ondersteunt bovendien expliciete intervalconfiguratie binnen 15–600s. Default600 bewijst niet dat iedere huidige mode600 gebruikt. WSL GET /health meet dit zonder iets te veranderen. Een waargenomen 15s-override mag niet automatisch worden verwijderd: daarvoor moet de eigenaar aangeven of die actieve override bewust moet blijven. Dat is een eventuele runtimeconfiguratiebeslissing, geen resterende onzekerheid over het staged defaultbronbeleid.

Focused resultaat: 5 passed; brede canonical suite: 475 passed / 1 socketbeperking. Zie remediation/qualification_policy.* en qualification_final_regression.*.
