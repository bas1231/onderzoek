# Permanente begrensde researchoperatie

De oorspronkelijke hourly-userunit is bewaard. Een eigen drop-in kiest de echte productie-entrypoints in een Linux user/mount/net/pid-namespace, met uitsluitend gekopieerde input en lokale Git-checkpoints. Normale production-mode/indexguards zijn niet afgezwakt. De publieke GET-broker kent uitsluitend de vooraf toegestane gratis bronnen. Modeltekst wordt niet als code uitgevoerd.

De bestaande hourlytimer verzamelt data en maakt een unieke duurzame reviewtaak. Een aparte Codex-timer controleert elke vijf minuten de queue. De worker gebruikt de bestaande ChatGPT-login, beschikbare Astra en hoge reasoning, zonder shell/apps/web/tools of API-keyfallback. Eén flock beschermt de worker, inclusief subprocessen. De receiver verwerkt modelresultaten in dezelfde isolatierun; kandidaatbesluiten en vervolgacties staan daar in NEXT_ACTIONS.json. Zij geven geen autorisatie voor orders, builds of vrije shellopdrachten. Nieuwe echte hourlyinput vormt de volgende trigger. De canonical owner-candidatebestanden worden niet automatisch met deze afgeleide besluiten overschreven.

Quota: echte machine-events leiden tot PAUSED_USAGE_LIMIT en vijf uur backoff; geen percentagescraper/reset/credits. Nieuwe collectoroutput kan tijdens een bezette worker als duurzame outbox wachten. Een volgende deliveryronde neemt die over. Corruptie en provenanceverschillen blokkeren zichtbaar. Opslag is lokaal; maak normale backups van knowledge/codex_runtime/runtime.sqlite (SQLite-consistente backup), niet alleen de Git-views. Een ontbrekende database wordt niet stil opnieuw opgebouwd.

Herstel: beide timers zijn enabled; Linger=yes. systemd moet beschikbaar zijn in een gestarte WSL-distro. Dit start Windows of een uitgeschakelde WSL-distro niet zelfstandig. Geen echte hostreboot uitgevoerd; procescrash, geërfde lock, stale lock, gedeeltelijke writes, idempotente completion en quota-resume zijn gericht getest. Collectoren blijven onafhankelijk van Codex-quota draaien. Meetgaten mogen geen ononderbroken prospectief experiment suggereren.

Volgen (alleen lezen):

```sh
journalctl --user -f -u prediction-research-hourly-director.service -u prediction-codex-supervisor.service
```

Veilig de Codex-queue pauzeren na een lopende worker: `systemctl --user stop prediction-codex-supervisor.timer`. Dit stopt bestaande collectoren niet. Hervatten: `systemctl --user start prediction-codex-supervisor.timer`. Een lopende worker niet onnodig onderbreken. Geen normal-mode hourly handmatig starten nadat de eigen drop-in is verwijderd: die oude checkpointtransport kan pushen.

Status van de browser-originroundtrip blijft afzonderlijk van de rechtstreekse Codex-researchlane. Een backend-healthcheck bewijst niet dat een zichtbare chat door Tampermonkey ontvangen wordt en in dezelfde consumer terugkomt.
