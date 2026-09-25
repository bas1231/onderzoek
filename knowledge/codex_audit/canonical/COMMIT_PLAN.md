# Lokale commitinstructies

HEAD tijdens herstel: `db6c0f3c98b0b8fbc8b89544c3745cfba311e8e6`. Baseline `80a5ff7` blijft ancestor. Canonical .git is binnen deze toolomgeving read-only; er zijn geen nieuwe canonical commits gemaakt.

`canonical_change_manifest.json` bevat de exacte 22 gewijzigde/toegevoegde code- en testpaden met basis-/eindhashes. `canonical_changes.patch` is uitsluitend de auditdelta ten opzichte van de gecontroleerde preflightwerkboom. De patch is **niet** bedoeld om opnieuw op de reeds gerepareerde bron toe te passen.

De oorspronkelijke staged index is byte-equivalent volgens `git diff --cached --binary`-hash. Alle niet-gerelateerde oorspronkelijke tracked bestanden matchen de preflight. Routerbestand heeft zowel oorspronkelijke staged consumer-routingwijzigingen als eigen unstaged reparaties; deze provenance is expliciet bewaard onder before/ en preflight.json.

## Script

`commit_locally.py` controleert HEAD, indexhash en alle canonical eindhashes; bij afwijking stopt het zonder reset/stash/clean. Het maakt zes lokale commits:

1. Gedragsregressies en gecorrigeerde testfixtures.
2. Weatherreceipt, coverage en prospectieve targetvaliditeit.
3. Fail-closed economics/proof-gate.
4. Executorpolicy, timeout en terminale queueafhandeling.
5. Consumer-routing en browserdelivery. **Deze commit bevat ook het reeds staged ownerwerk in command_router.py**, als basis van de gerelateerde routingreparatie. De andere staged ownerbestanden blijven staged en worden niet meegenomen.
6. Auditrapporten, red/green evidence, manifests, diffs en continuatieplan.

Er wordt niet gepusht. Actieve hooks blokkeren het script; deze worden niet stilzwijgend uitgeschakeld. Het script is getest in een tijdelijk lokaal Git-fixture: zes commits, behouden unrelated staged ownerfile en correcte routerinhoud (`commit_plan_test.json`). Dit testbewijs is geen canonical commit.

Uitvoeren vanuit de normale lokale WSL-terminal nadat de inhoud is beoordeeld:

```bash
python3 ~/prediction_research_prod/knowledge/codex_audit/canonical/commit_locally.py
```

Dit is een afzonderlijk proces; een fout sluit de interactieve terminal niet af. Als HEAD/index inmiddels gewijzigd zijn of een commit gedeeltelijk lukt, NIET de index terugzetten: lees de melding en maak het resterende commitplan opnieuw passend bij de werkelijke toestand.
