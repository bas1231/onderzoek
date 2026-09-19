# Execution-first Kalshi scan — 2026-09-19

Status: **NO_PROVEN_EDGE**

Doel: na de methodologische verschuiving naar execution-first zoeken naar cashflows die werkelijk kunnen worden vastgelegd, in plaats van primair naar midpoint- of probability-afwijkingen te zoeken.

## Samenvatting

Deze scan vond nog **geen kandidaat met bewezen positieve `net_locked_edge`**. Wel zijn drie lanes duidelijker geworden:

1. **Exhaustieve mutually-exclusive baskets** zijn schoon en goed automatiseerbaar, maar de bekeken 3-way sportmarkten hadden momenteel een kleine overround in plaats van een ondergeprijsde gegarandeerde basket.
2. **State-locked sportthresholds** blijven zeer interessant omdat de payoff na het overschrijden van een monotone threshold deterministisch kan worden. De huidige browser/search-evidence was echter niet voldoende om simultane executable bid/ask + size voor een reeds gelockte strike te bewijzen; geen edgeclaim.
3. **Treasury-threshold display anomalies** zagen er op categorie-/zoekpagina's soms onmogelijk uit, maar andere snapshots toonden dunne of lege books. Zonder uitvoerbare tegenzijde zijn dit display/stale-data candidates, geen economische edge.

## Lane A — exhaustieve 3-way baskets

Voor regulation-time soccer zijn home/draw/away mutually exclusive en exhaustief als de contractregels exact dezelfde 90-minuten+stoppage-time scope gebruiken.

Voorbeelden uit Kalshi-webdata tijdens deze scan:

- Tottenham vs Aston Villa: zichtbare YES-zijden ongeveer 49c + 27c + 27c = 103c op de individuele markt-snapshot; huidige combo-weergave zat rond 102c totaal.
- Brighton vs Arsenal: zichtbare YES-zijden ongeveer 56c + 21c + 25c = 102c.
- Andere actuele EPL/MLS/EFL/Ligue-1 combo-overzichten zaten overwegend rond 101–103c voor de drie YES-outcomes.

Theoretische settlementcashflow van één YES op iedere uitkomst = $1.00. De bekeken baskets kosten dus al >$1.00 vóór fees: `net_locked_edge < 0`.

Een alternatieve basket koopt één NO op alle drie de outcomes. Omdat precies één outcome YES wordt, betalen dan precies twee NO-contracten uit: gegarandeerde settlementcashflow = $2.00. De bekeken zichtbare NO-zijden lagen veelal rond 201–202c totaal. Ook deze lane was dus licht negatief vóór fees.

### Implicatie

Dit is een goede automatische scanner omdat de payout exact is. Trigger alleen wanneer:

`sum(executable_yes_asks) + fees + buffer < 100c`

of, voor N exhaustieve uitkomsten:

`sum(executable_no_asks) + fees + buffer < (N-1)*100c`.

De NO-basket lijkt op sommige actuele 3-way markten dichter bij de theoretische grens te liggen dan de YES-basket, maar een 1–2c bruto verschil rond de grens is nog onvoldoende vanwege fees en legging/fill-risk.

## Lane B — state-locked monotone thresholds

Voor monotone sporttotalen geldt zodra de live score een `Over X.5`-threshold heeft overschreden en de relevante score onder de contractregels niet meer kan dalen:

`Payout(YES Over X.5) = $1` in alle toegestane resterende game-states, behoudens expliciete void/cancel/fair-price/finality branches.

Deze lane past goed bij execution-first research omdat geen probabilistische voorspelling meer nodig is zodra de state werkelijk locked is.

Tijdens de scan was Houston–Texas Tech relevant als voorbeeld: publieke bronnen lieten een eindscore 28–26 (54 totaal) zien, terwijl Kalshi's totalenpagina verschillende thresholds inclusief 53.5/54.5 exposeerde. De zoek-/browserlaag leverde echter **geen betrouwbare simultane executable quote + size voor de specifieke gelockte 53.5-strike**. Een externe mirror toonde ogenschijnlijk stale/live waarden en is daarom nadrukkelijk niet als bewijs gebruikt.

### Vereiste proof

Een state-lock candidate wordt pas positief wanneer dezelfde timestamp/snapshot bewijst:

- officiële/game-state voldoet aan lock-conditie;
- contractregel maakt die state monotone en settlement-safe;
- concrete ticker/strike is nog tradable;
- executable YES ask + size aanwezig;
- `1.00 - ask - fee - slippage/fill buffer > 0`;
- opportunity lifetime is lang genoeg voor retail-Starlink latency;
- finality/score-correction/VAR/review/void branches zijn afgedekt.

Status: `STRUCTURAL_CANDIDATE`, maar **NO_PROVEN_EDGE**.

## Lane C — Treasury-threshold anomalies

Kalshi categorie-/zoekresultaten lieten tijdens de scan enkele ogenschijnlijk niet-monotone Treasury-threshold percentages zien, wat theoretisch strijdig zou zijn met nested events. Een hogere yield-threshold kan niet werkelijk waarschijnlijker zijn dan een lagere threshold als settlementsemantiek identiek is.

Andere markt-/secondary snapshots toonden echter dunne boeken, soms lege bids en grote spreads. Daardoor kan een mooie probability/display anomaly volledig niet-executable zijn.

Regel: categoriekaart, Chance, midpoint of stale index is alleen discovery. Zonder concrete executable bid/ask + size en gelijke rules is dit geen candidate edge.

Status: `DISPLAY_OR_STALE_ANOMALY_UNRESOLVED`; economisch `NO_PROVEN_EDGE`.

## Fee-check

Kalshi's algemene prediction-market takerfee is prijsafhankelijk (`round up(0.07 * C * P * (1-P))` volgens de fee schedule; specifieke producten kunnen afwijken). Hierdoor moet een multi-leg basket doorgaans meer dan slechts 1–2c bruto ruimte hebben voordat een conservatieve `net_locked_edge` positief kan worden.

Makerfees kunnen lager zijn, maar een makerconstructie is niet automatisch locked: niet alle legs hoeven te vullen en queue/legging risk ontstaat. Daarom mag een theoretische maker-basket niet als gegarandeerde execution-edge worden behandeld zonder fillmodel en prospectieve data.

## Infrastructuurfit

Voor de beschikbare setup (ROG Strix i9 + snelle Starlink, geen colocatie/HFT) krijgen de volgende kandidaten prioriteit:

- deterministic/exhaustive baskets;
- state-locks met opportunity lifetime van seconden of langer, niet microsecond-races;
- payoff identities die lokaal zwaar kunnen worden doorgerekend;
- kansen met marge ruim boven fee/spread/buffer;
- relation/theorem search waarbij compute belangrijker is dan colocatie.

Deprioriteer opportunities die alleen bestaan bij queue dominance of sub-millisecond reaction.

## Eerstvolgende scannerregels

1. Enumerateer alle mutually-exclusive/exhaustive events en bereken zowel YES- als NO-basketfloor.
2. Filter vooraf op voldoende top-of-book size en brutomarge groter dan een conservatieve fee+slippage threshold.
3. Detecteer monotone live thresholds die door een verified game-state locked zijn; toets settlement/finality vóór prijscheck.
4. Log alleen point-in-time simultaneous snapshots als economische evidence.
5. Rangschik op `net_locked_edge * executable_quantity`, maar rapporteer payout-floor, quantity en opportunity lifetime afzonderlijk.

## Bronnen geraadpleegd

- Kalshi live/category/market pages, 2026-09-19.
- Kalshi Pro help: markets screener toont live Yes/No prices, top-of-book sizes, spread, volume en depth filters.
- Kalshi Pro help: maker/taker order-book views.
- Kalshi fee schedule / fee help.

Geen derdepartij-mirror is gebruikt als execution proof.
