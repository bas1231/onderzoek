# Execution fee-regime watch + maker-trigger completion

Datum: 2026-09-19
Status: **STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE**

## Kern

Veel formeel geldige payout-identiteiten sterven pas in de execution-laag door takerfees. Daarom moet de fee-state zelf als **live marktvariabele** worden behandeld en niet als statische configuratie.

Twee aanvullende execution-lanes zijn daarom relevant:

1. **dynamic fee-regime watch** — iedere payout-candidate opnieuw waarderen wanneer series/event fee-state of een fee waiver verandert;
2. **maker-trigger -> bounded completion** — één geschikte leg passief laten vullen en pas na die fill de overige legs direct completeren wanneer de volledige basket nog steeds conservatief `net_locked_edge > 0` heeft.

Geen van beide is op dit moment een bewezen winststrategie.

---

## 1. Dynamic fee-regime watch

### Primaire API-evidence

De actuele Kalshi documentatie exposeert expliciet:

- `GET /series/fee_changes` — series fee changes;
- `GET /events/fee_changes` — event fee overrides;
- eventvelden `fee_type_override` en `fee_multiplier_override`;
- marketveld `fee_waiver_expiration_time`;
- feevelden moeten dus point-in-time aan de candidate worden gebonden.

Bronnen:
- https://docs.kalshi.com/llms.txt
- https://docs.kalshi.com/api-reference/events/get-multivariate-events
- https://help.kalshi.com/en/articles/13823805-fees

### Economische implicatie

Voor een formele payout-floor geldt:

`net_locked_edge = payout_floor - executable_cost - fees - slippage_buffer - execution_risk_buffer`

Een candidate kan dus economisch van teken veranderen **zonder prijswijziging** wanneer de effectieve fee verandert.

Daarom moet iedere structurele candidate-index opnieuw worden doorgerekend bij:

- series fee change;
- event-level fee override;
- start/einde van een fee waiver;
- maker/taker fee-regime wijziging.

Dit is vooral relevant voor gross gaps van circa 1-5 cent, omdat juist daar fees vaak het verschil maken tussen positief en negatief.

### Drie-invalshoekencheck

1. **Semantiek/API:** PASS — fee changes/overrides/waiver metadata zijn machineleesbaar gedocumenteerd.
2. **Economisch:** PASS — de fee-term staat rechtstreeks in de lower-boundberekening en kan het teken van `net_locked_edge` veranderen.
3. **Live execution:** NOT PROVEN — in deze onderzoeksronde is geen verse fee-change aangetroffen die een concrete basket fee-net positief maakte.

Status blijft daarom `STRUCTURAL_CANDIDATE / NO_PROVEN_EDGE`.

---

## 2. Maker-trigger -> bounded completion

### Idee

In plaats van alle legs als taker te kopen:

1. kies de leg waarop passieve uitvoering de meeste fee/spread-waarde kan besparen;
2. plaats uitsluitend een **post-only/resting** order op die leg;
3. monitor queue position + fills;
4. na iedere partial/full maker fill: lees direct verse L2 voor alle completion-legs;
5. completeer alleen als een conservatieve FOK/IOC-prijsgrens de hele payoutconstructie nog `net_locked_edge > 0` laat;
6. anders: geen automatische promotie naar edge; registreer open leg-exposure en de unwind/hold-uitkomst als execution risk.

Kalshi exposeert queue position voor resting orders via prijs-tijdprioriteit en ondersteunt batch-orderinterfaces/order-management. De V2-order shape in de actuele SDK/spec bevat onder meer `post_only` en `time_in_force`; runtime-implementatie moet exact tegen de actuele OpenAPI worden gevalideerd voordat er geld wordt gebruikt.

Bronnen:
- https://docs.kalshi.com/llms.txt
- https://kalshi.com/pro/help/managing-orders-and-positions
- https://app.unpkg.com/kalshi-typescript@3.26.0/files/docs/OrdersApi.md

### Waarom dit mogelijk beter bij Strix + Starlink past

De strategie probeert niet als eerste een zichtbare arbitrage-gap te pakken. De passieve leg wacht in de queue. De latencykritische stap begint pas **na een eigen fill** en bestaat uit een vooraf begrensde completion-check.

Dat is nog steeds latencygevoelig, maar minder afhankelijk van colocatie dan pure taker-vs-taker races, mits:

- de completion books voldoende diep zijn;
- de candidate niet binnen enkele tientallen milliseconden verdwijnt;
- de resterende legs met een harde cost ceiling kunnen worden uitgevoerd;
- adverse selection na maker fill niet systematisch de basket vernietigt.

### Illustratieve fee-aritmetiek uit de handmatige CPI-scan

Een eerder geobserveerde, NIET simultaan-L2-bewezen 3-leg payout identity gebruikte ongeveer:

- leg A: 84c
- leg B: 54c
- leg C: 59c
- totale cost: 197c
- bewezen settlement floor onder de hypothese: 200c
- gross gap: 3c per complete basket

Voor 100 baskets en de algemene takerformule `0.07*C*P*(1-P)`, met cent-roundup per order, zijn de indicatieve takerfees ongeveer:

- A: $0.95
- B: $1.74
- C: $1.70
- totaal: $4.39

Gross locked profit voor 100 baskets = $3.00, dus all-taker is negatief vóór slippage.

Als B volledig als fee-free maker zou vullen en A+C daarna als taker compleet kunnen worden tegen dezelfde prijzen:

- completion fees A+C ≈ $2.65
- gross locked profit = $3.00
- resteert slechts ≈ $0.35 vóór slippage, latency en legging risk.

Als op de makerleg wél de algemene quadratic makerfee-coëfficiënt `0.0175` van toepassing is, komt B indicatief rond $0.44 fee voor 100 contracts en verdwijnt dit kleine voordeel alweer.

**Conclusie van dit rekenvoorbeeld:** live `fee_type`, `fee_multiplier`, maker/taker-status en rounding zijn beslissend. Dit voorbeeld is geen execution proof en geen trade-aanbeveling.

### Falsificatie

Kill/deprioritize deze execution-lane wanneer prospectieve data laat zien dat:

- maker fills vooral optreden vlak vóór ongunstige repricing;
- completion na fill zelden fee-net positief beschikbaar blijft;
- completion-window korter is dan conservatief haalbare retail-latency;
- partial fills een groter expected loss veroorzaken dan de fee-besparing;
- queue time/capital usage de materialiteitsgate niet haalt.

### Prospectief experiment

Per structurele candidate loggen:

- fee regime + exacte effective timestamp;
- makerleg en reden van keuze;
- queue position door de tijd;
- maker fill timestamp/quantity;
- simultane completion-L2 direct vóór/na fill;
- fee-correcte `completion_cost_ceiling`;
- FOK/IOC-simulated fillability;
- 100ms/250ms/500ms/1s/2s post-fill completion survivability;
- eventuele open exposure als completion faalt;
- absolute locked profit, capacity en capital-time return.

Geen live-money promotie vóór een prospectieve shadow-corpus laat zien dat de lower bound herhaalbaar positief blijft.

---

## Onderzoeksprioriteit

**Hoog:** dynamic fee-state revaluation van reeds bewezen payout identities.

**Midden/hoog:** maker-trigger completion op 2-3 leg deterministic floors, vooral wanneer één makerfill voldoende fee bespaart om de basket van negatief naar positief te trekken.

**Laag:** complexe multi-maker baskets waarbij meerdere passieve legs eerst moeten vullen; legging- en adverse-selectionrisico groeit dan snel.

Economic status: `NO_PROVEN_EDGE`.
