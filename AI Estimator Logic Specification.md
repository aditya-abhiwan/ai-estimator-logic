AI Estimator Logic Specification (Platform-Agnostic)

Purpose
This document defines the deterministic pricing logic for a roofing AI estimator supporting both Insurance and Retail pricing modes with a fixed global margin and residential-only tax percentage.

Core Rules
- Two pricing modes: Insurance and Retail
- Margin is fixed at 33% and applied globally at the end
- Tax is a percentage
- Tax applies only to residential properties
- No per-line markup or dynamic margin adjustments

Inputs Per Job
- pricing_mode: insurance | retail
- margin: 0.33 (locked)
- tax_rate: residential tax percentage as a decimal, for example 0.05 for 5%
- is_residential_property: true | false
- components (array):
  - name
  - quantity
  - unit
  - insurance_unit_price
  - retail_unit_price

Pricing Logic
Rule 1: Unit Price Selection
If pricing_mode = insurance
  unit_price = insurance_unit_price
Else
  unit_price = retail_unit_price

Rule 2: Line Cost Calculation
line_cost = quantity * unit_price

Rule 3: Base Cost Calculation
base_cost = SUM(all line_costs)

Rule 4: Global Margin Application
price_after_margin = base_cost * 1.33

Rule 5: Residential Tax Percentage
If is_residential_property = true
  final_price = price_after_margin * (1 + tax_rate)
Else
  final_price = price_after_margin

Single Formula Representation
FinalPrice =
(SUM(Quantity_i * Price_i(mode))) * 1.33 * (1 + effective_tax_rate)

Where effective_tax_rate is tax_rate for residential properties and 0 for non-residential properties.

Compliance Guardrails
- Margin applied once at the end only
- Tax is a percentage, not a fixed dollar amount
- Tax applies only to residential properties
- Identical quantities regardless of pricing mode
- Pricing variance derives solely from unit price selection
- No hidden or compounding markups

Use Cases
- Insurance replacement cost calculations
- Retail customer pricing
- AI-driven estimating engines
- Spreadsheet and CRM integrations

End of Specification
