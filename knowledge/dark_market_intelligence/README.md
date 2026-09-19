# Dark Market Intelligence

Status: **INTELLIGENCE ONLY — NOT AN EXECUTION LANE**

Deze map bewaart uitsluitend rechtmatig verkregen intelligence over dark-web/illicit-market mechanismen die relevant kunnen zijn voor prediction-market research.

## Doel

Leer van marktmechanismen, incentives, governance, escrow/reputation, settlement, fraud/scam patterns, market lifecycle, participant behavior en resilience in illegale of dark-web markten, en vertaal alleen de overdraagbare economische inzichten naar legaal testbare hypotheses op reguliere prediction markets.

## Toegestane bronklassen

- publieke academische papers;
- publieke onderzoeksdatasets;
- forensische publicaties;
- threat-intelligence/OSINT-rapporten;
- historische archieven die rechtmatig beschikbaar zijn;
- publiek indexeerbare beschrijvingen van marktmechanismen.

## Niet toegestaan in deze lane

- financieren of gebruiken van illegale markten;
- handelen/kopen/verkopen;
- faciliteren van illegale transacties;
- credential-/identiteitsmisbruik;
- ongeautoriseerde toegang;
- operationele exploit-instructies.

## Recordregel

Iedere entry krijgt minimaal:

```yaml
id: DMI-...
source_class: DARK_MARKET_INTELLIGENCE
status: FACT_VERIFIED|OBSERVED|HYPOTHESIS_UNTESTED|TESTED_NEGATIVE
mechanism: ...
transferable_prediction_market_hypothesis: ...
source: ...
confidence: ...
legal_execution_path: none|regular_prediction_market_test
```

Een DMI-entry kan discovery beïnvloeden maar nooit zelfstandig een live-execution gate passeren.
