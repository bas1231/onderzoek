# Research stop — informed flow / alleged insider-flow lane

Datum: 2026-09-19
Status: **PAUSED BY USER / NO_PROVEN_EDGE**

## Stopbesluit

De gebruiker heeft expliciet gevraagd het onderzoek op dit punt te stoppen. Deze notitie markeert het einde van de huidige informed-flow onderzoeksronde. Geen verdere uitbreiding, webresearch, hypothesegeneratie, bouw of validatie binnen deze lane totdat de gebruiker dit later opnieuw expliciet vraagt.

## Laatste canonieke researchoutput

Hoofdbestand:

- `knowledge/kalshi/INFORMED_FLOW_SHADOWING_2026-09-19.md`
- commit: `0c5f8a881bdbf1a1a1420386e320ec1f979c134c`

Kernstatus:

- informed/toxic orderflow kan economisch relevanter zijn als **adverse-selection warning** dan als contrarian signal;
- tweede kandidaatmechanisme is **cross-market information propagation**: een publieke aggressive-flow event in markt A gebruiken als trigger om formeel gerelateerde markten B/C op achterlopende repricing te screenen;
- blind whale-following en blind whale-fading blijven lagere prioriteit door selectie, latency, liquidity-provider confounding en false positives;
- alle claims blijven `NO_PROVEN_EDGE` totdat historische execution-realistische replay, untouched validation en prospectieve shadow de relevante net-edge bewijzen.

## Drie-hoekenstatus bij stop

1. **Literatuur / economisch mechanisme:** research-positive; grote/abnormale flow en order-flow toxicity hebben empirische ondersteuning, maar `large trader = insider` is niet gerechtvaardigd.
2. **Meetbaarheid / data:** research-positive; publieke trade-side/size/timestamp- en sequence-safe L2-data maken een Informed Flow Score / toxicityscore technisch toetsbaar.
3. **Execution / falsificatie:** nog onbewezen; resterende predictieve informatie na retail-observeerbare latency, fees, spread, queue/fill en cross-market repricing is niet aangetoond.

## Harde regels bij eventuele hervatting

- Geen individuen deanonymiseren of als insider bestempelen op basis van vermoedens.
- Alleen publiek observeerbare marktdata en aggregate flow gebruiken.
- Geen blind contrarian rule tegen grote traders.
- Pre-register IFS/toxicityfeatures en thresholds vóór outcome-inspectie.
- Test historische execution-realistische replay -> validation -> untouched holdout -> prospectieve shadow.
- Meet 100ms/250ms/500ms/1s/2s/5s/30s/5m markouts waar data dit ondersteunt.
- Voor Strix + Starlink alleen lanes behouden waarvan de opportunity lang genoeg leeft voor retail execution.
- Status blijft `NO_PROVEN_EDGE` totdat netto edge na alle kosten en executionrisico's prospectief standhoudt.

## Resume pointer

Als dit onderzoek later wordt hervat, begin dan bij:

`knowledge/kalshi/INFORMED_FLOW_SHADOWING_2026-09-19.md`

en controleer eerst nieuwe/negatieve evidence voordat nieuwe hypotheses worden toegevoegd.
