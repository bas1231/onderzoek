# Kalshi high-probability favorite scan — 2026-09-19

Status: **TESTED_NEGATIVE / NO_PROVEN_EDGE**

## Vraag

Bestaan er op 2026-09-19 actuele Kalshi-sportcontracten waarbij een redelijke onafhankelijke kansschatting **>=80%** is, terwijl Kalshi materieel goedkoper noteert (screeningdoel: grofweg Kalshi <=75–80¢ of een robuuste gap van circa >=5 procentpunt)?

Dit is alleen candidate discovery. UI/search-snippets/third-party mirrors gelden nadrukkelijk niet als executionbewijs; voor promotie zijn contemporaneous Kalshi bid/ask/L2, fees/depth en verdere validation nodig.

## Methode

Conform `AGENTS.md` en `methodology/RESEARCH_PROTOCOL.md` is iedere ogenschijnlijke hit vanuit meerdere hoeken gefalsificeerd:

1. Kalshi/public prediction-market price reference;
2. sportsbook moneyline omgerekend naar no-vig fair probability waar beide zijden beschikbaar waren;
3. een of meer model/projection-bronnen waar beschikbaar;
4. controle op stale/indexed/mirror-data en bronconflicten.

Geen enkele UI/referenceprijs hieronder wordt als executable L2 geclaimd.

## Gecontroleerde examples

### Texas A&M vs Kentucky
- Kalshi reference: ~88%.
- Sportsbook -1100 / +680 => no-vig Texas A&M ~87.7%.
- ESPN FPI lag hoger (~94%), maar andere model/market-referenties lagen rond 88–89%.
- Besluit: de aantrekkelijke 6pp-gap was hoofdzakelijk één model tegenover marktconsensus. **Geen robuuste mispricing.**

### Virginia vs West Virginia
- Kalshi/reference: ~77%.
- Sportsbook -390 / +320 => no-vig Virginia ~77.0%.
- Een model lag rond 80%, een andere projection rond 86%.
- Besluit: model disagreement, geen onafhankelijke consensus >=80% tegenover een duidelijk lagere markt. **TESTED_NEGATIVE voor deze snapshot.**

### Louisiana-Monroe vs Southeastern Louisiana
- Een oudere/geïndexeerde Kalshi-teampagina leek Louisiana-Monroe rond 48% te tonen terwijl sportsbooks ongeveer 80–82% impliceerden.
- Actuelere odds-comparison toonde Kalshi zelf rond 81%; sportsbook -546 / +378 => no-vig Louisiana-Monroe ~80.2%.
- Dit was een **stale/indexed-data false positive**, geen 30pp edge.
- Belangrijke les: search snippets/team pages kunnen sterk achterlopen en mogen nooit direct price-violation bewijs zijn.

### Georgetown vs Richmond
- Kalshi reference: ~82% Richmond.
- Sportsbook -520 / +350 => no-vig Richmond ~79.1%.
- Modelreference ~82–83%.
- Besluit: Kalshi niet aantoonbaar goedkoop; eerder rond/fractioneel boven externe fair reference. **Geen edge.**

### Bowling Green vs Iowa State
- Kalshi/reference rond 93–95% afhankelijk van snapshot/venue display.
- Sportsbook -2800 / +1300 => no-vig Iowa State ~93.1%.
- Modellen rond 94.5–96.6%.
- Besluit: enkele modelpunten boven markt, maar geen robuuste >=5pp gap en geen executionbewijs. **Geen promotie.**

### Tulane vs Kansas State
- Kalshi odds-comparison reference ~90.9% Kansas State.
- Sportsbook -1400 / +1000 => no-vig Kansas State ~91.1%.
- Modellen waren sterk verdeeld (ongeveer 78% tot ~93%).
- Besluit: markt en no-vig sportsbook vrijwel gelijk; model disagreement. **Geen edge.**

### Sacred Heart vs Elon
- Een oudere directe Kalshi-searchsnapshot liet Elon rond 80–81% zien.
- Nieuwere prediction-market mirrors/aggregators lagen rond ~90%; sportsbook ranges varieerden, met no-vig grofweg ~79.5–83.9%; Dimers ~87%.
- Door snapshot/staleness-conflict ontbreekt betrouwbaar contemporaneous Kalshi executionbewijs.
- Besluit: **UNPROVEN**, niet promoveren. Een oude 80¢ snapshot mag niet worden gecombineerd met later model/oddsbewijs.

### Purdue vs UCLA
- Kalshi odds-comparison reference ~88.5% UCLA.
- Andere market references rond ~90%; Covers preview rond 85%; Dimers eerder rond 87%.
- Besluit: geen consensus dat fair probability materieel boven Kalshi ligt. **Geen edge.**

## Falsificatie-uitkomst

De scan vond geen kandidaat die tegelijk:

- door meerdere onafhankelijke bronnen plausibel >=80% fair probability heeft;
- materieel lager op Kalshi geprijsd lijkt;
- niet verklaard wordt door stale/mirror/UI-data of model disagreement.

De grootste visuele afwijking (Louisiana-Monroe ~48% versus ~81%) verdween volledig na freshness-controle en is juist sterke negative evidence voor de anti-pattern `UI/search snapshot == executable price`.

## Economische/executionstatus

- Geen actuele Kalshi L2 uit deze webscan.
- Geen contemporaneous executable ask/depth proof.
- Geen fee/slippage/partial-fill gate uitgevoerd omdat geen candidate de eerdere signal/market-reference falsificatie overleefde.
- Geen replay, validation, untouched holdout of prospective shadow.

Daarom blijft de economische status **NO_PROVEN_EDGE**.

## Bronnen / provenance (online, geraadpleegd 2026-09-19)

- Kalshi public market/team pages (`kalshi.com`).
- Covers odds comparison (`covers.com`).
- Action Network matchup odds (`actionnetwork.com`).
- Oddschecker (`oddschecker.com`).
- Dimers model pages (`dimers.com`).
- FanDuel Research / numberFire where cited during candidate checks (`fanduel.com`).

## Herbruikbare regel

Een toekomstige high-probability scanner moet candidate generation en proof scheiden:

`external model/odds divergence -> freshness check -> no-vig independent consensus -> exact Kalshi ticker/rules -> contemporaneous executable L2 -> fees/depth -> replay/validation/shadow`.

Als een ogenschijnlijke edge alleen bestaat door een oudere UI/search snapshot, wordt zij direct `TESTED_NEGATIVE` voor die snapshot en niet verder economisch gepromoveerd.
