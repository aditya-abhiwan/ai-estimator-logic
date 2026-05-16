FPR Mathematical Model for Roof Replacement Price Estimating

This document defines the FPR pricing model used by the Python estimator.

The model keeps the original FPR roof geometry, material quantity, complexity, and labor logic, but uses one deterministic final pricing rule:

FinalPrice = ((material_cost + labor_cost) * 1.33) * (1 + residential_tax_rate)

Tax is a percentage and is applied only for residential properties. For non-residential properties, the effective tax rate is 0%.

The 33% margin is fixed and applied once at the end. There is no overhead multiplier and no per-line markup.

## 1. Notation And Inputs

- A_plan = plan or horizontal roof area in square feet.
- pitch p = rise/run, for example 6:12 means p = 6 / 12 = 0.5.
- n_facets = number of roof facets.
- alpha = complexity increase per additional facet.
- w = waste factor.
- For each component i:
  - u_i = selected unit price.
  - c_i = unit coverage.
  - qty_i = calculated quantity.
- L_base = labor cost per square foot.
- tax_rate = residential tax percentage as a decimal, for example 0.05 for 5%.
- is_residential_property = whether the estimate is for a residential property.
- Fixed margin = 33%.

## 2. Geometry Conversion

Convert pitch into a slope factor:

```text
slope_factor = sqrt(1 + p^2)
```

Convert plan area into actual roof surface area:

```text
A_roof = A_plan * slope_factor
```

Example:

```text
pitch = 6:12
p = 6 / 12 = 0.5
slope_factor = sqrt(1 + 0.5^2) = 1.1180

A_plan = 2,000 sq ft
A_roof = 2,000 * 1.1180 = 2,236.07 sq ft
```

## 3. Material Quantities

For each component with area coverage:

```text
qty_i = A_roof / c_i
```

Apply waste:

```text
qty_i_with_waste = qty_i * (1 + w)
```

Combined formula:

```text
qty_i_with_waste = (A_roof / c_i) * (1 + w)
```

Components that do not have area coverage must use quantity overrides.

Examples:

- Pipe boot flashing
- Hip and ridge bundles
- Drip edge
- Starter
- Step flashing
- Valley metal
- Vents
- Caps
- Nails
- Caulking
- Paint

## 4. Unit Price Selection

The unit price is selected from the pricing workbook.

Insurance mode:

```text
if insurance_price exists:
    unit_price = insurance_price
else:
    unit_price = upper_price
```

Retail mode:

```text
low = lower_price
likely = (lower_price + upper_price) / 2
high = upper_price
```

If a component has only one price, that price is treated as both lower and upper.

## 5. Line Cost

Each component line is calculated as:

```text
line_cost_i = qty_i_with_waste * unit_price_i
```

For quantity override components:

```text
line_cost_i = override_quantity_i * unit_price_i
```

There is no per-line markup.

## 6. Material Cost

Material cost is the sum of all component line costs:

```text
material_cost = sum(line_cost_i)
```

Expanded:

```text
material_cost = sum(qty_i * unit_price_i)
```

## 7. Complexity And Facets

Complexity is based on roof facet count:

```text
complexity_multiplier = 1 + alpha * (n_facets - 1)
```

The default alpha used by the Python estimator is:

```text
alpha = 0.02
```

Example:

```text
n_facets = 5
alpha = 0.02

complexity_multiplier = 1 + 0.02 * (5 - 1)
complexity_multiplier = 1.08
```

## 8. Labor Cost

Labor cost is optional.

If labor is used:

```text
labor_cost = L_base * A_roof * complexity_multiplier
```

If labor is not provided:

```text
labor_cost = 0
```

## 9. Base Cost

Base cost is material plus labor:

```text
base_cost = material_cost + labor_cost
```

## 10. Final Price

The final price applies the fixed 33% margin once, then applies tax as a percentage only for residential properties:

```text
effective_tax_rate = tax_rate if is_residential_property else 0
FinalPrice = base_cost * 1.33 * (1 + effective_tax_rate)
```

Expanded:

```text
FinalPrice = (material_cost + labor_cost) * 1.33 * (1 + effective_tax_rate)
```

Important rules:

- Margin is applied only once.
- Margin is fixed at 33%.
- Tax is a percentage.
- Tax applies only to residential properties.
- No per-line markup is allowed.
- No overhead multiplier is used.
- No compounding formula like `(1 + overhead) * (1 + margin)` is used.

## 11. Price Ranges

The estimator supports three retail price levels:

- Low: lower unit prices from the workbook.
- Likely: midpoint between lower and upper unit prices.
- High: upper unit prices from the workbook.

Insurance mode uses the insurance price when available, otherwise it falls back to the upper unit price.

## 12. Full Pipeline

```text
1. roof_area = plan_area * sqrt(1 + p^2)
2. quantity = (roof_area / coverage) * (1 + waste_factor)
3. unit_price = selected price from pricing mode
4. line_cost = quantity * unit_price
5. material_cost = sum(line_cost)
6. labor_cost = labor_rate * roof_area * complexity_multiplier
7. effective_tax_rate = tax_rate if residential else 0
8. final_price = (material_cost + labor_cost) * 1.33 * (1 + effective_tax_rate)
```

This is the model developers should use for automated quote generation.
