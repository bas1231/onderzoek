# ForecastEx Block/RFQ access watch — 2026-09-22

Status: `WATCH / ACCESS_BLOCKER`
Economic conclusion: `NO_PROVEN_EDGE`

## Question
Do ForecastEx's new Block Trading, RFQ and temporary block-fee changes create a practically accessible execution path for this project, or do participant/access requirements make the lane non-actionable at the current budget?

## Primary-source facts

1. **Block Trading rule exists and is certified.** The CFTC filing list shows ForecastEx's filing `Amending Rulebook to allow for Block Trading`, received 2026-09-02 and **Certified 2026-09-17**.
   - Source: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules

2. **RFQ access is described as a Member function, not a general Customer function.** The 2026-09-08 CFTC filing description says the rule change permits **Members** to use ForecastEx's Request for Quote (RFQ) system to create quote-request messages expressing interest in a Forecast Market. As checked on 2026-09-22, the CFTC filing list still showed this item as `10 Day Review`.
   - Source: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules

3. **The Block Trading Fee Holiday is not yet safe to treat as effective merely because its proposed start date is 2026-09-22.** CFTC filing 63737 says ForecastEx is amending the fee schedule to add a Block Trading Fee Holiday for Block Trades executed from 2026-09-22 through 2026-12-01. As checked on 2026-09-22, the filing still showed `10 Day Review`; therefore runtime economics must not assume the fee is active without an effective/certified source.
   - Source: https://www.cftc.gov/IndustryOversight/IndustryFilings/TradingOrganizationRules/63737

4. **Ordinary Customer access is through an FCM/Sponsored FCM.** ForecastEx Rule 304 states that a person who is not eligible to become a Member may enter Forecast Contracts if they become a Customer of an FCM Member or Sponsored FCM. Rule 406 states that all Customer Bids must be transmitted to ForecastEx by the Customer's FCM Member.
   - Current public rulebook URL checked: https://data.forecastex.com/regulatory/ForecastEx_LLC_Rulebook.pdf
   - Note: the publicly linked rulebook version observed during this check was dated 2026-07-16 and therefore predates the September block-trading certification. It is useful for the Member/Customer access model, not as proof of the final September block-rule text.

5. **Direct ForecastEx Membership is outside this project's budget envelope.** ForecastEx's current membership page says Members must maintain operational resources, designate Authorized Traders/Representatives and are subject to a **minimum Clearing Fund deposit of USD 250,000**.
   - Source: https://forecastex.com/members

6. **Retail/customer Forecast Contract trading is available through Interactive Brokers, but no public customer RFQ/block workflow was located in the IBKR material checked.** IBKR documents ForecastTrader, Web/TWS API support, ScaleTrader and normal Forecast Contract order entry. Those public pages do not establish that an ordinary customer can originate ForecastEx RFQs or negotiate/report Block Trades.
   - Sources:
     - https://www.interactivebrokers.com/predictionmarkets/en/home.php
     - https://www.interactivebrokers.com/docs/web-api/v1/endpoints/event-contracts/markets-and-strikes
     - https://www.interactivebrokers.com/en/trading/scaletrader-forecast-contracts.php

## Red-team interpretation

The rule change is real, but the project does **not** currently have evidence that the new execution path is available to a retail Customer at the current budget.

Direct Member access is not an economic fit because the published minimum Clearing Fund deposit alone is orders of magnitude above the project's budget. The remaining possibility is that an FCM exposes block/RFQ functionality to Customers or aggregates Customer interest, but that has not been proven from current public documentation.

The fee holiday also must not be treated as current executable economics until its effective status is confirmed. A proposed date inside a filing is not sufficient evidence when the public filing status still reads `10 Day Review`.

## Decision

- Do **not** build a ForecastEx block-trading strategy now.
- Keep this as a `WATCH` trigger, not an active candidate.
- Do not infer off-book/block liquidity from visible CLOB depth.
- Do not apply the proposed fee holiday in any PnL calculation until current effective status is proven.
- Ordinary ForecastEx/IBKR CLOB research remains separate and may continue under existing execution-realism gates.

## Resurrection / promotion conditions

Re-open this lane only if at least one of the following changes is documented:

1. An FCM used by this project exposes Customer RFQ or Block Trade functionality.
2. ForecastEx/FCM documentation establishes a block minimum or aggregation mechanism compatible with the project's budget.
3. The block fee holiday is shown by a current effective/certified fee schedule and materially changes executable economics.
4. Point-in-time evidence captures a Customer-accessible RFQ/block quote alongside contemporaneous CLOB depth, fees and fill/eligibility constraints.

Until then: `ACCESS_BLOCKER`, `NO_PROVEN_EDGE`.
