# ForecastEx block/RFQ access kill-check — 2026-09-22

Status: `ACCESS_BLOCKED_FOR_CURRENT_DEPLOYMENT / RESURRECT_ON_EXPLICIT_FCM_SUPPORT`
Economic conclusion: `NO_PROVEN_EDGE`

## Question

Do ForecastEx's newly certified Block Trading rules, proposed RFQ functionality and proposed Block Trading Fee Holiday create a practically accessible execution lane for this project (budget ~EUR 250), or is the lane blocked by participant class / membership / implementation status before any economic test is justified?

## Primary-source findings

### 1. Block Trading itself is certified

The CFTC DCM rule-filing register lists ForecastEx's filing **"Amending Rulebook to allow for Block Trading"** with receipt date 2026-09-02 and status **Certified** on 2026-09-17.

Source: CFTC DCM filings register, FEX entry.

This proves that a ForecastEx block-trading rule change exists. It does **not** prove that this project's retail/FCM-customer path can initiate or receive block trades, nor does it establish an executable minimum size.

### 2. RFQ is not yet established as available to this project

The CFTC register lists a separate FEX filing dated 2026-09-08 whose description says the rule change permits **Members** to use ForecastEx's Request for Quote (RFQ) system to create quote-request messages expressing interest in a Forecast Market. As checked on 2026-09-22, the register still shows **10 Day Review**.

This is important for two reasons:

- the public filing description scopes RFQ to **Members**;
- the filing is not yet shown as Certified in the CFTC register at this point-in-time.

Therefore RFQ must not be treated as a currently proven executable path for this project's customer account.

### 3. The Block Trading Fee Holiday is also not yet proven effective

The CFTC filing page for FEX filing 63737 describes an amendment adding a **Block Trading Fee Holiday** for Block Trades executed between **2026-09-22 and 2026-12-01**. However, as checked on 2026-09-22, the CFTC register still shows the filing status as **10 Day Review**.

Therefore the intended holiday period is not sufficient evidence that the fee holiday is currently effective. Current fee economics remain `UNKNOWN` until certification/effective status and the applicable clean fee schedule are captured.

### 4. Direct ForecastEx membership is economically incompatible with this project

ForecastEx's current public Membership page says Members are subject to a **minimum Clearing Fund deposit of $250,000**. The ForecastEx Rulebook also states that each Member's Clearing Fund contribution is subject to a minimum size of at least $250,000.

Given this project's approximately EUR 250 research/trading budget, direct ForecastEx Membership is not a viable access path.

This is an access/capital constraint, not a statement about general retail customer eligibility.

### 5. Ordinary customer access through an FCM does exist

ForecastEx Rule 304 states that a person who is not eligible to become a ForecastEx Member may enter Forecast Contracts by becoming a Customer of an FCM Member or Sponsored FCM. Rule 403 says customer Bids are submitted through the FCM/Sponsored FCM via an Authorized Trading User.

So the ordinary Forecast Contract path remains potentially accessible through an intermediary even though direct membership is not.

What is **not** established by those rules is that an ordinary FCM Customer can use the new Member-facing RFQ functionality or participate in block trades on customer instructions.

### 6. The currently documented IBKR customer/API path exposes ordinary Event Contract orders, not a ForecastEx RFQ/block flow

Interactive Brokers' current Event Contract Web API documentation explicitly supports ForecastEx Event Contract discovery and standard order submission through the ordinary account order endpoint. Its ForecastEx order example opens/closes positions by buying YES/NO contracts and uses the normal order payload.

The current public Event Contract documentation reviewed on 2026-09-22 contains purpose-built discovery/rules endpoints and ordinary order submission, but no documented ForecastEx customer RFQ endpoint, block-trade endpoint, RFQ-response workflow, block minimum-size parameter, or customer-facing block execution workflow.

This is **not** proof that no FCM can ever support a customer block/RFQ service. It is sufficient to fail closed for this project's current autonomous API deployment: the identified, documented customer API route does not presently establish access to the new Member-facing RFQ/block execution lane.

## Fail-closed decision

Do **not** build a ForecastEx block/RFQ execution strategy for the current deployment.

Current gate state:

- Block Trading rule exists: `PASS`
- Direct Membership feasible for project budget: `FAIL`
- Ordinary FCM customer access to Forecast Contracts: `PASS`
- IBKR ordinary ForecastEx Event Contract API access: `PASS / STANDARD_ORDER_PATH`
- Customer/API access to ForecastEx RFQ: `NOT_DOCUMENTED / FAIL_CLOSED`
- Customer/API access to ForecastEx Block Trading: `NOT_DOCUMENTED / FAIL_CLOSED`
- Other FCM customer RFQ/block support: `UNKNOWN`
- Block minimum size: `UNKNOWN`
- RFQ minimum size / response semantics: `UNKNOWN`
- Block Trading Fee Holiday currently effective: `UNKNOWN / CFTC still 10 Day Review at capture time`
- Point-in-time executable block/RFQ quotes: `MISSING`
- Net executable edge: `NOT TESTABLE`

For the present project constraints, this trigger is therefore `ACCESS_BLOCKED_FOR_CURRENT_DEPLOYMENT`. No market-data scanner, execution adapter, strategy code or specialist capacity should be allocated to this lane while those access gates remain closed.

## Resurrection conditions

Reopen the lane only on new primary evidence that changes a decisive dependency, for example:

1. a qualified FCM explicitly documents that ordinary customers may originate/respond to ForecastEx RFQs or submit customer block trades;
2. a customer-accessible API/electronic workflow for that functionality is documented;
3. minimum quantity/notional is documented and compatible with the project budget;
4. the relevant RFQ/block and fee-holiday filings are certified/effective and current fees are captured;
5. executable point-in-time RFQ/block quotes or fills can then be captured without paid/nonpublic access.

Until one of those conditions changes, repeated investigation of ForecastEx block/RFQ economics is duplicate work and should be suppressed by Failure Memory / resurrection logic.

No paid action, account opening, broker contact, trade, wallet action or live execution is authorized by this note.

Economic conclusion remains `NO_PROVEN_EDGE`.
