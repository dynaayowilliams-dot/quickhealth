# QuickHealth business plan for cfo.ai

## Purpose and current status

QuickHealth is a hackathon prototype for structured clerking and triage history-taking. It asks adaptive history questions, applies a rules-based urgency layer, checks completeness and contradictions, and can generate a structured note. It is not a diagnostic product, does not provide medical advice, and must only be used with fictional cases at this stage.

This is a planning draft, not a forecast based on actual sales, customer interviews, audited costs, or a validated market size. There are no paying customers or revenue figures established in the project materials. Every modeled figure below is an **ASSUMPTION** or a calculation from assumptions. Do not present these figures as actuals.

## Target customer

The target customers are clinics and health facilities in Nigeria, including facilities with community health workers and dedicated antenatal and paediatric units. The likely day-to-day users are nurses, community health workers, and other health workers who take histories. The modeled paying customer is one clinic or facility account; an individual staff member is not counted as a separate customer.

The intended value is a more structured history-taking workflow and a consistent clerking note. Urgency remains determined by the rules-based safety layer. A health professional must review outputs. The product is not intended to diagnose or replace clinical judgment.

## Proposed pricing to test

These prices are **ASSUMPTIONS for customer discovery**, not researched market rates or approved prices. The naira conversions use an **ASSUMPTION exchange rate of ₦1,600 per US$1**. Replace that rate with the rate used by the business when presenting a live forecast.

| Option | Assumed price in USD | Assumed price in NGN | Modeling note |
|---|---:|---:|---|
| Per completed clerking session | **ASSUMPTION: US$1.00** | **ASSUMPTION: ₦1,600** | Charge only when a clerking session is completed. |
| Per clinic per month | **ASSUMPTION: US$75/month** | **ASSUMPTION: ₦120,000/month** | Flat monthly clinic subscription. Session allowance or fair-use cap must be agreed during a pilot. |

The Base and Growth scenarios below use the per-clinic monthly option. The per-session option is an alternative to test and is not added on top of the subscription revenue.

## Cost assumptions

### Inference cost per completed session

`cost_report.py` estimates model cost from recorded input and output token counts and the configured model's rates. The privacy-safe local aggregate contained **0 completed sessions with recorded token usage** when this draft was prepared. There is therefore no observed per-session cost to use yet.

For the model, use an **ESTIMATE / ASSUMPTION of US$0.01 per completed session**, or **₦16** at the assumed exchange rate above. This is a placeholder, not an observed API cost. Replace it with the average from `cost_report.py` after representative fictional sessions have recorded token usage. Actual charges can vary by model, token volume, caching, and provider pricing.

### Monthly infrastructure

These are monthly **ASSUMPTIONS**, not AWS quotes:

| Cost item | Assumed USD/month | Assumed NGN/month | Basis |
|---|---:|---:|---|
| Hosting | **US$25** | **₦40,000** | Planning allowance for one small EC2 host, its disk, and public access. Confirm with the AWS calculator and the hackathon allowance before launch. |
| Database | **US$0** | **₦0** | SQLite runs on the same host; there is no separate managed database in this draft. This does not include backups or durable storage. |
| Tracing | **US$0** | **₦0** | Assumes tracing remains within the hackathon or included allowance. Verify any plan limits or overage charges. |
| **Total infrastructure** | **US$25** | **₦40,000** | Sum of the three assumed monthly costs. |

Inference is shown separately from fixed infrastructure, then combined with infrastructure in the scenario cost row. The hosting estimate excludes unexpected bandwidth, snapshots, taxes, support, and additional services.

## Monthly scenario assumptions

Every driver in this section is an **ASSUMPTION**:

- Exchange rate: **₦1,600 per US$1**.
- Clinic subscription: **US$75 (₦120,000) per clinic per month**.
- Inference cost: **US$0.01 (₦16) per completed session**.
- Hosting, database, and tracing combined: **US$25 (₦40,000) per month**.
- Base: **5 clinic customers**, averaging **250 completed sessions per clinic per month**.
- Growth: **15 clinic customers**, averaging **400 completed sessions per clinic per month**.
- Starting cash for runway: **US$5,000 (₦8,000,000)**.
- Monthly fixed operating costs, excluding hosting and inference: **US$1,500 (₦2,400,000)** for product maintenance, support, and basic administration.

The Growth case assumes both more clinics and higher usage per clinic. It is an illustrative scenario, not a target supported by a sales pipeline. Customer acquisition, payment collection, taxes, foreign-exchange fees, and working-capital timing are not modeled.

## Monthly Base and Growth outputs

Revenue uses the clinic-per-month subscription. “Infrastructure plus inference cost” equals the US$25 monthly infrastructure assumption plus assumed sessions multiplied by US$0.01 per session. Gross profit equals revenue less that combined cost. Gross margin equals gross profit divided by revenue.

| Metric | Base | Growth |
|---|---:|---:|
| Customers (clinic accounts) | **ASSUMPTION: 5** | **ASSUMPTION: 15** |
| Completed sessions per month | **CALCULATED: 1,250** | **CALCULATED: 6,000** |
| Revenue per month | **CALCULATED: US$375 / ₦600,000** | **CALCULATED: US$1,125 / ₦1,800,000** |
| Infrastructure plus inference cost per month | **CALCULATED: US$37.50 / ₦60,000** | **CALCULATED: US$85 / ₦136,000** |
| Gross profit per month | **CALCULATED: US$337.50 / ₦540,000** | **CALCULATED: US$1,040 / ₦1,664,000** |
| Gross margin | **CALCULATED: 90.0%** | **CALCULATED: 92.4%** |

These are calculations from the assumptions above, not actual performance. Values in the companion CSV are easier to import into a financial model.

## Simple runway estimate

Runway is modeled as starting cash divided by monthly net cash burn. Monthly net cash burn equals assumed fixed operating costs minus gross profit. Hosting and inference are already deducted in gross profit, so they are not subtracted a second time.

| Metric | Base | Growth |
|---|---:|---:|
| Starting cash | **ASSUMPTION: US$5,000 / ₦8,000,000** | **ASSUMPTION: US$5,000 / ₦8,000,000** |
| Monthly fixed costs, excluding infrastructure and inference | **ASSUMPTION: US$1,500 / ₦2,400,000** | **ASSUMPTION: US$1,500 / ₦2,400,000** |
| Monthly net cash burn | **CALCULATED: US$1,162.50 / ₦1,860,000** | **CALCULATED: US$460 / ₦736,000** |
| Simple runway | **CALCULATED: about 4.3 months** | **CALCULATED: about 10.9 months** |

This simplified estimate assumes constant monthly revenue, costs, and collections. It excludes taxes, financing, setup costs, customer acquisition costs, bad debt, churn, and any changes in usage. It is not a cash-flow forecast.

## Risks and requirements before real use

- **Clinical and regulatory risk:** the red-flag rules are not clinician-reviewed (`reviewed_by_clinician: false`). A qualified clinician familiar with current Nigerian guidance must review the rules and workflow. Obtain appropriate Nigerian regulatory and privacy review before any real-world use.
- **No clinical validation:** passing the scripted software checks does not show that the product is safe, accurate, or improves outcomes. Live model behavior with real conversations has not been tested.
- **Data privacy and access:** the current prototype uses a shared SQLite database and exposes saved cases in its UI. Do not enter real patient data. A shared access code is not user-specific access control.
- **Model quality and safety:** the language model may ask unsuitable questions or format inaccurate notes. It does not set urgency, but the rules themselves may miss or misinterpret language.
- **Customer and pricing uncertainty:** the customer, willingness to pay, sales cycle, and preferred pricing option have not been validated. The prices and customer counts here are assumptions, not market statistics.
- **Cost uncertainty:** the US$0.01 inference estimate is not measured. Actual token usage, model choice, hosting charges, tracing charges, and FX conversion may materially change margins.
- **Reliability and operations:** the single-server SQLite setup has no high availability or managed backup in this model. Server failure, disk loss, or poor connectivity could interrupt access or lose records.
- **Runway uncertainty:** the assumed starting cash and fixed costs are placeholders. Replace them with actual bank balance, payroll, support, and operating expenses before using the runway output.

## Suggested cfo.ai modeling inputs

Import `cfo_ai_inputs.csv` as a monthly planning input. Use the rows marked `ASSUMPTION` as editable drivers and the rows marked `CALCULATED FROM ASSUMPTIONS` as checks or target outputs. Keep Base and Growth as separate scenarios. Replace assumptions with verified customer, billing, token, infrastructure, and cash data as they become available.
