# Execution-first cashflow discovery

Datum: 2026-09-19
Status: **METHODOLOGY — NO_PROVEN_EDGE**

## Kernverschuiving

Zoek niet primair naar prijsafwijkingen, rare midpoints of theoretische mispricings. Zoek primair naar **cashflows/payoffs die op het beslismoment werkelijk kunnen worden vastgelegd en die na executionkosten een positieve ondergrens hebben**.

De centrale vraag is dus niet:

> "Waar wijkt de prijs af?"

maar:

> "Welke positie of portfolio kan ik nu daadwerkelijk construeren, wat betaalt die in iedere toegestane settlementstate uit, en blijft de slechtste netto cashflow positief na alle kosten en uitvoeringsrisico's?"

Een prijsafwijking is alleen discovery. Een kans wordt pas economisch interessant wanneer de executable cashflow zelf positief is.

## Positieve EV is de admission rule

Er bestaat **geen minimum dagwinst of minimum absolute winstbedrag** voordat een kans onderzoekswaardig wordt.

- Iedere conservatief aantoonbare `net EV > 0` is relevant, ook als de winst slechts centen per episode bedraagt.
- `€100+/dag` is een later **portfolio-schaaldoel**, geen threshold voor een individuele edge.
- Een kleine positieve edge wordt niet gekilled omdat zij klein is. Zij kan lager worden gerangschikt op capacity of opportunity cost, maar blijft als geldige edge/candidate behouden zolang de economics positief en execution-realistisch zijn.
- Meerdere onafhankelijke kleine edges mogen worden gestapeld; portfolio-aggregatie is een expliciet geldige schaalroute.
- Schaal, capacity, frequentie, capital lock en return per capital-day zijn dus **karakteriserings- en rankingvariabelen**, geen admission-gates.

De bewijsstandaard blijft identiek voor kleine en grote edges.

## Prioriteitsvolgorde

Voor structurele/algebraïsche kansen geldt voortaan bij voorkeur:

`payoff/settlement semantics -> constructeerbare cashflow -> simultaneous executable bid/ask + L2 depth -> fees -> slippage -> partial-fill/legging risk -> latency/finality -> netto worst-case payout -> validation -> scale/capacity characterization`

Niet:

`midpoint anomaly -> veronderstelde edge -> execution achteraf`

## Minimale execution-aware berekening

Voor iedere kandidaat moet waar relevant worden vastgelegd:

- exacte settlement/payofffunctie per leg;
- bewezen relatie tussen de legs;
- koop-/verkooprichting per leg;
- gelijktijdige executable bid/ask, niet alleen midpoint/UI chance/last trade;
- beschikbare quantity/depth op de benodigde prijsniveaus;
- fees per leg;
- slippagebuffer;
- partial-fill/legging scenario;
- relevante latency/finality/collateral-risico's;
- gegarandeerde of conservatieve netto payout-floor;
- maximale executable quantity waarop die floor nog geldt.

Een nuttige kernmaat is:

`net_locked_edge = worst_case_settlement_cashflow - executable_cost - fees - slippage_buffer - execution_risk_buffer`

Voor een hedge/short-constructie wordt dezelfde logica met de juiste cashflowtekens toegepast.

Alleen wanneer `net_locked_edge > 0` onder conservatieve, point-in-time aannames is een kandidaat execution-positive genoeg om naar de volgende gate te gaan. **Hoe klein die positieve edge is, verandert deze admission rule niet.**

## Scale/materiality characterization — ranking, geen kill-gate

Een positieve locked edge kan klein, kapitaalintensief of zeldzaam zijn. Dat beïnvloedt hoe hoog we haar prioriteren en hoeveel engineeringcapaciteit zij verdient, maar niet of zij als echte positieve-EV-route mag blijven bestaan.

Bereken daarom aanvullend minimaal:

- `executable_capacity_contracts`;
- `absolute_locked_profit_usd = net_locked_edge_per_contract * executable_capacity_contracts`;
- `capital_locked_usd`;
- `days_to_expected_cash_release`;
- `return_on_locked_capital`;
- `return_per_capital_day` en waar zinvol annualized return;
- verwachte herhaalbaarheid/frequentie van dezelfde opportunity class;
- potentiële portfolio-combinatie met andere onafhankelijke kleine edges.

Een 1c edge met vijf contracts en lange capital lock kan laag-prioriteit zijn, maar wordt **niet afgewezen omdat de absolute winst klein is**. Alleen wanneer fricties/risico's de netto EV niet-positief maken, execution onrealistisch is, of expliciet onderbouwde opportunity cost verdere research niet rechtvaardigt, mag zij worden geparkeerd of gekilled.

Voor de lokale Strix/Starlink-doelstelling krijgen kansen hogere prioriteit wanneer zij tegelijk:

1. een formeel/verifieerbaar positieve floor hebben;
2. voldoende depth/capacity hebben voor hogere absolute dollars;
3. relatief kort capital lock hebben of vroeg collateral/cash vrijgeven zonder de payoffgarantie te verbreken;
4. lang genoeg executable blijven voor retail-netwerklatency;
5. prospectief herhaalbaar zijn.

Dit is een **prioriteitsrangschikking**, geen bewijs- of toelatingsdrempel.

## Bevinding uit handmatige Kalshi-tests — 2026-09-19

Tweede onderzoeksronde over Moment-SOS, Möbius, Walsh/Fourier, Hodge, Optimal Transport, MaxEnt/Ising, absorbed-martingale en Hawkes liet zien:

- algebraïsche/statistische methoden vinden relatief gemakkelijk prijsverschillen, midpoint-curl en synthetische/directe afwijkingen;
- deze verschillen verdwenen in de bekeken voorbeelden meestal zodra echte bid/ask, fees, spread, slippage of fill-risico werd meegenomen;
- een eerder waargenomen bruto CPI-cashflowkandidaat van circa `198c -> 200c` was daarom geen bewezen execution-edge; de quotes veranderden en de bruto marge was onvoldoende om meerdere takerlegs en fees overtuigend te overleven;
- de bottleneck is dus niet alleen het vinden van afwijkingen, maar vooral het vinden van een **uitvoerbare payoffconstructie waarvan de netto cashflow na alle fricties positief blijft**;
- fee-free exhaustive partitions bevestigen bovendien dat zelfs een echte below-par basket lage capacity of lange settlementtijd kan hebben; zulke kansen blijven relevant maar moeten apart op schaal en capital efficiency worden gekarakteriseerd.

Status van deze bevinding: `RESEARCH_POSITIVE` voor de methodologische richting, maar overall economische status blijft `NO_PROVEN_EDGE`.

## Discovery-prioriteit

Geef meer prioriteit aan kansen met één of meer van deze eigenschappen:

1. deterministische of formeel begrensde payout;
2. meerdere productpaden naar dezelfde settlementcashflow;
3. payoff dominance / locked lower bound;
4. voldoende dikke L2-depth om alle legs werkelijk te vullen;
5. marge die ruim groter is dan fees + spread + redelijke executionbuffer;
6. opportunity lifetime die past bij retail-infrastructuur;
7. weinig of beheersbaar legging/partial-fill-risico;
8. hogere absolute profit bij de werkelijk executable capacity;
9. goede capital efficiency / korte settlementhorizon;
10. combineerbaarheid met andere onafhankelijke positieve-EV-routes.

Geef lagere prioriteit aan:

- midpoint-only afwijkingen;
- verschillen kleiner dan de plausibele totale executionkosten;
- opportunities die alleen bestaan als alle legs exact tegelijk tegen theoretische prijzen vullen;
- races die uitsluitend met colocatie, gespecialiseerde low-latency networking of HFT-infrastructuur realistisch zijn;
- signalen zonder duidelijk pad naar een verhandelbare netto cashflow;
- formeel positieve kansen met zeer lage capacity of extreem lange capital lock **alleen qua prioriteit, niet als automatische kill**.

## Relatie tot bestaande methoden

Möbius, Walsh/Fourier, Hodge, SOS, Optimal Transport en vergelijkbare technieken blijven nuttig, maar hun rol is vooral **candidate generation en formele payoff-analyse**. Zij mogen een anomalie niet automatisch als edge promoveren.

De gewenste architectuur wordt daarom conceptueel:

`candidate discovery -> payout theorem/identity -> executable cashflow construction -> L2/fees/fill verification -> conservative net edge -> validation/holdout -> scale/capital-efficiency characterization -> prospective shadow -> micro-live`

MaxEnt/Ising, martingale- en Hawkes-methoden kunnen daarnaast kandidaten rangschikken of adverse-selection/flowrisico signaleren, maar vervangen geen execution proof.

## Bewijsstandaard

Een agent mag pas spreken over een execution-positive candidate wanneer point-in-time evidence de volledige benodigde constructie ondersteunt. Ontbrekende simultane depth, onbekende fees, onzekere settlementsemantiek of niet-bewezen legging maken de status `UNKNOWN`, `STRUCTURAL_CANDIDATE` of `NO_PROVEN_EDGE`, niet `PROVEN_EDGE`.

Een execution-positive candidate hoeft **geen minimum absolute winst of minimum dagwinst** te halen om als economische edge erkend te kunnen worden. Na bewijs worden capacity, frequentie, capital efficiency en portfolio-bijdrage afzonderlijk gerapporteerd. Een kleine bewezen edge blijft een bewezen edge; schaal is een volgende optimalisatielaag.