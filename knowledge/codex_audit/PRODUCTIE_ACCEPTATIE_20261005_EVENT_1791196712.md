# Productieacceptatie — tussenstand 5 oktober 2026

Status: **FAIL / nog niet geaccepteerd**. Dit verslag registreert ontvangen uitvoeringsbewijs; het is geen nieuwe testuitvoering.

## Waargenomen bewijs

- Taak: `DEV-PRED-CONT-NEXT-c8dcbf91be52fd2957116bd6`.
- Resultaatevent: `1791196712-62230058835e`.
- Uitkomst: `FAIL exit=2`; onderliggende controle `python rc=1`.
- Gecontroleerde broncommit: `bdea57b293335c8772af1a105274ce6bdfa2f76f`, vastgelegd in de onveranderlijke projectspecificatie.
- De statusregistratie van `DEV-PRED-REPAIRS-TARGETED-VERIFY-R2-20261005` bevat `PASS`. De compacte uitvoer bewijst op zichzelf niet alle afzonderlijke bron- en operatievoorwaarden voor deze oudere taak.
- De statusregistratie van `DEV-PRED-REQUESTED-REPAIRS-FINAL-ACCEPT-20261005` bevat `CLAIMED`; `final_proven=false`. CLAIMED is geen bewijs dat deze taak nog draait: event `1791195396-f6bca2f8d8c6` meldde al FAIL bij de laatste productievergelijking.
- Productie wijkt af van de gecontroleerde bron voor `control/codex_supervisor/supervisor.py` en `control/hourly/candidate_reporting.py`.
- Zes pincontroles in productie slagen niet: candidate_dispatch, build_wake, model_quality_gate, measurement_wake, supervisor en astra_autonomous_review. De controle behandelt een ontbrekend bestand, symlink of niet overeenkomende hash als ongeldig; de compacte uitvoer onderscheidt deze oorzaken niet.

## Relatie met eerdere eindacceptatie

De eerdere eindacceptatie vergeleek met broncommit `8511127a874f323cc46cf701b2e9286d287f0b9a` en rapporteerde 77 gewijzigde/niet-gevolgde paden: 19 gelijk, 11 verschillend en 47 niet aanwezig in die bron. Dit zijn verschillende controles en bronmomenten; de aantallen mogen niet worden opgeteld.

De gerichte hersteltest bewijst dus nog geen correcte productie-installatie. Ook is hiermee geen volledige scout-naar-bouw-naar-meting-naar-rapportage-keten bewezen.

## Vervolg en grenzen

De bestaande taak `DEV-PRED-PROD-DIFF-INVENTORY-20261005-E001` inventariseert read-only de productieverschillen tegen de broncommit van de mislukte eindacceptatie. Haar uitvoeringsresultaat is op het moment van dit verslag nog niet ontvangen. Een eventuele PASS van die inventarisatietaak betekent uitsluitend dat de inventarisatie is uitgevoerd.

Geen dubbele inventarisatie of volledige systeemtest gestart. Productie blijft behouden: geen reset, opschoning, overschrijving, deployment of servicewijziging. Eerst moeten de concrete verschillen en hun herkomst worden beoordeeld; de bestaande acceptatiecriteria blijven van kracht.
