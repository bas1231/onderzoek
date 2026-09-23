# CLOB tail demand / screening rent — 2026-09-23

Status: `RESEARCH_POSITIVE_MECHANISM / NO_PROVEN_EDGE`

## Bron
- Zang, Chengqi; Andrade, Gabriel P.; Nakajima, Tomoyuki (2026), *Who Aggregates Information? Screening, Rent, and the Coexistence of CLOB and AMM Prediction Markets*, arXiv:2609.20017, versie geplaatst 2026-09-17.
- Publiek/gratis academisch bronmateriaal.

## Nieuwe evidence
De paper rapporteert transaction-level evidence van een grote prediction-market CLOB waarin market makers volgens de auteurs niet primair verdienen aan klassieke spread capture, maar aan het dragen van een ondergeprijsde zijde tot settlement. Hun interpretatie is behavioral tail demand. Het model voorspelt daarnaast dat competitieve CLOB-quotes informed flow uit het book kunnen screenen, terwijl informed flow naar een LMSR/AMM kan migreren.

Dit is nieuw ten opzichte van de huidige Git-memory: repository-search op de titel en op `tail demand` gaf geen bestaand record.

## Relevantie voor bestaande lanes
- `KAL-FLB-002`: mechanistische ondersteuning voor het idee dat favorite/longshot-achtige vraag niet als simpele directional trading rule moet worden behandeld, maar mogelijk als inventory/market-making premium.
- maker/microstructure: spread capture alleen is een onvolledig economisch model; settlement inventory en adverse selection moeten afzonderlijk worden gemeten.
- informed_flow: venue-mechanisme kan flow selecteren; flow op een CLOB hoeft dus geen representatieve steekproef van alle geïnformeerde handel te zijn.

## Semantiek/source
Observatie: de auteurs rapporteren maker-P&L die vooral samenhangt met het dragen van de ondergeprijsde zijde tot settlement.
Inferentie: behavioral tail demand kan een maker-premium financieren waar klassieke noise-flow-spreadlogica tekortschiet.
Hypothese: vergelijkbare prijsbucket/category-asymmetrie kan op andere CLOB prediction venues bestaan.

Niet bewezen: dat het empirische venue/resultaat direct naar Kalshi, ForecastEx of andere venues transfereert; dat een huidige executable quote positieve netto expected value heeft; dat maker fills beschikbaar zijn zonder ongunstige selectie.

## Point-in-time / reproduceerbaarheid
Deze run heeft geen eigen transaction-level dataset gereproduceerd. Het resultaat blijft academische externe evidence en is geen onafhankelijke reproductie. Een serieuze vervolgtest moet vooraf price-buckets/categories, maker/taker-classificatie, settlement-P&L, markouts en fees vastleggen en point-in-time data gebruiken.

## Economics / execution
Geen economische promotie. Voor een echte edge zijn minimaal nodig:
1. prospectieve of untouched maker-fill evidence;
2. queue-ahead/fill modelling;
3. post-fill markouts en adverse selection;
4. inventory exposure tot settlement;
5. fees/rewards/slippage/capital lock;
6. out-of-sample stabiliteit per category/price bucket.

De bestaande ledgerregel `maker zijn == edge` blijft volledig gelden.

## Research Director
Classificeer als nieuwe mechanistische evidence en als input voor `TASK-FLB-001`, niet als nieuwe strategie. Geen strategy-build of live execution gerechtvaardigd.

Economic conclusion: `NO_PROVEN_EDGE`.
