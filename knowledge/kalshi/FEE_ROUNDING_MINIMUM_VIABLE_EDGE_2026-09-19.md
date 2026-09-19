# Fee rounding → minimum viable edge / size

Datum: 2026-09-19
Status: **RESEARCH_POSITIVE / EXECUTION RULE**

## Kern

Voor execution-first scanning mag een gross payout gap niet alleen met een continue feeformule worden vergeleken. Kalshi's fee schedule definieert:

`fee = round_up(k * C * P * (1-P))`

waar:

- `C` = aantal contracts;
- `P` = contractprijs in dollars;
- `round_up` = afronden naar de volgende cent.

Voor S&P 500 / Nasdaq-100 is in de gepubliceerde specifieke fee table `k = 0.035`; voor de algemene fee is `k = 0.07`.

Bronnen:
- https://kalshi.com/docs/kalshi-fee-schedule.pdf
- https://help.kalshi.com/en/articles/13823805-fees

Daarom is de **minimum viable gross edge afhankelijk van prijs, quantity, aantal takerlegs en fillfragmentatie**.

---

## Reduced-fee indexvoorbeeld

Bij `k=0.035` en `P=0.50` is de niet-afgeronde takerfee asymptotisch:

`0.035 * 0.5 * 0.5 = $0.00875 = 0.875c per contract`.

Maar de absolute fee wordt naar de volgende hele cent afgerond.

Illustratief, bij één enkele fee-berekening per leg:

| Quantity C | Totale fee bij P=0.50 | Fee per contract |
|---:|---:|---:|
| 1 | $0.01 | 1.00c |
| 2 | $0.02 | 1.00c |
| 5 | $0.05 | 1.00c |
| 10 | $0.09 | 0.90c |
| 20 | $0.18 | 0.90c |
| 50 | $0.44 | 0.88c |
| 100 | $0.88 | 0.88c |
| 500 | $4.38 | 0.876c |

Dus een **twee-leg all-taker locked floor rond 50c/50c** heeft vóór slippage ongeveer minimaal:

`~1.75c gross edge per complete basket`

nodig wanneer quantity groot genoeg is om rounding te amortiseren.

Bij zeer kleine quantity is de hurdle eerder ~2c per complete basket doordat iedere leg minimaal naar 1 cent fee afrondt.

Voor drie takerlegs rond midprice ligt de asymptotische fee-hurdle al rond:

`3 * 0.875c = 2.625c per complete basket`

vóór slippage/legging buffer.

Dit verklaart waarom bruto 1-3c payout identities vaak verdwijnen zodra execution correct wordt gemodelleerd.

---

## Price dependence

De fee is lager aan de randen omdat `P(1-P)` kleiner wordt.

Voor de indexcoëfficiënt `k=0.035` is de asymptotische fee per contract ongeveer:

- P=0.10 / 0.90: `0.315c`;
- P=0.25 / 0.75: `0.65625c`;
- P=0.50: `0.875c`.

Daarom mag de scanner geen vaste regel gebruiken zoals “alle gross gaps onder 2c weggooien”.

De correcte filter is per candidate:

`exact_rounded_fee(quantity, price, fee_regime)`

voor iedere leg.

---

## Fragmentation risk

De schedule formuleert fee over een trade en rondt omhoog naar de volgende cent. Wanneer een gewenste quantity in meerdere executions/fills uiteenvalt, kan herhaalde rounding de werkelijk betaalde fee verhogen ten opzichte van één theoretische berekening over de volledige quantity.

Daarom:

- geen fee berekenen alsof alle depth één fill vormt wanneer dat niet point-in-time bewezen is;
- log fillfragmentatie;
- bereken een conservatieve `fragmentation_fee_upper_bound` vóór economic promotion;
- makerfee-rounding en eventuele latere reimbursement niet behandelen als gegarandeerde realtime cashflow tenzij eligibility en uiteindelijke credit bewezen zijn.

De gepubliceerde schedule vermeldt expliciet dat overmatige makerfee door rounding onder voorwaarden later kan worden terugbetaald wanneer de cumulatieve reimbursement boven een minimum uitkomt. Dat is geen reden om de upfront execution-floor optimistischer te maken.

---

## Scannerregel

Voor iedere candidate en target quantity `Q`:

1. simuleer werkelijke L2-consumptie per prijsniveau;
2. bepaal executions/fill shards conservatief;
3. bereken fee per execution volgens het actuele fee regime;
4. round iedere fee volgens de exchange-regel;
5. som fees over alle legs/fills;
6. bereken pas daarna `net_locked_edge`.

Extra velden:

- `gross_edge_per_basket`
- `fee_floor_per_basket`
- `fee_rounding_drag`
- `fragmentation_fee_upper_bound`
- `minimum_quantity_for_positive_net_edge`
- `max_quantity_before_depth_slippage_kills_edge`

Hierdoor krijgt iedere structurele relation een **viable quantity interval** in plaats van alleen een ja/nee edge-label.

---

## Drie-invalshoekencheck

### 1. Bron/semantiek

**PASS.** De feeformule en `round up = rounds to the next cent` staan expliciet in de gepubliceerde Kalshi fee schedule.

### 2. Onafhankelijke rekencheck

**PASS.** Directe berekening laat zien dat de effective fee per contract bij kleine quantities merkbaar boven de continue asymptoot kan liggen en naar de asymptoot convergeert wanneer C groeit.

### 3. Execution

**STRUCTUREEL RELEVANT, EMPIRISCHE FRAGMENTATION NOG TE METEN.** De precieze gerealiseerde rounding drag hangt af van hoe orders daadwerkelijk over counterparties/price levels/executions worden gevuld. Prospectieve fill-data is nodig om een realistische fragmentation distribution te leren.

---

## Implicatie voor huidige research

Voor de nieuwe S&P/Nasdaq range-threshold dominance lane:

- all-taker gross crosses rond 0-1c krijgen zeer lage prioriteit rond midprice;
- ~2c crosses kunnen alleen na exacte price/quantity fee calculation worden beoordeeld;
- 3c+ gross crosses verdienen eerder een L2-check, maar zijn nog steeds geen edge vóór slippage/depth;
- maker-trigger completion kan juist interessant zijn wanneer één makerleg voldoende fee bespaart om de candidate over de zero-line te tillen.

Dit is een **execution rule**, geen bewezen winststrategie. Overall economic status blijft `NO_PROVEN_EDGE` totdat prospectieve candidates de volledige gates halen.
