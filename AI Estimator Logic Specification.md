AI Estimator Logic Specification (Platform-Agnostic)

Purpose
This document defines the deterministic pricing logic for a roofing AI estimator supporting both Insurance and Retail pricing modes with a fixed global margin.
Core Rules
• Two pricing modes: Insurance and Retail
• Margin is fixed at 33% and applied globally at the end
• No per-line markup or dynamic margin adjustments
Inputs Per Job
- pricing_mode: insurance | retail
- margin: 0.33 (locked)
- components (array):
  • name
  • quantity
  • unit
  • insurance_unit_price
  • retail_unit_price
Pricing Logic
Rule 1: Unit Price Selection
If pricing_mode = insurance
  unit_price = insurance_unit_price
Else
  unit_price = retail_unit_price
Rule 2: Line Cost Calculation
line_cost = quantity × unit_price
Rule 3: Base Cost Calculation
base_cost = SUM(all line_costs)
Rule 4: Global Margin Application
final_price = base_cost × 1.33
Single Formula Representation
FinalPrice =
( Σ (Quantity_i × Price_i(mode)) ) × 1.33
Compliance Guardrails
• Margin applied once at the end only
• Identical quantities regardless of pricing mode
• Pricing variance derives solely from unit price selection
• No hidden or compounding markups
Use Cases
• Insurance replacement cost calculations
• Retail customer pricing
• AI-driven estimating engines
• Spreadsheet and CRM integrations
End of Specification

