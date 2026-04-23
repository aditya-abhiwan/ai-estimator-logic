from __future__ import annotations

import json

import streamlit as st

import roof_pricing as pricing


st.set_page_config(
    page_title="FPR Roof Pricing Estimator",
    page_icon="",
    layout="wide",
)


def money(value: float) -> str:
    return f"${value:,.2f}"


@st.cache_data(show_spinner=False)
def load_prices() -> dict[str, list[pricing.ComponentPrice]]:
    return pricing.load_component_prices()


@st.cache_data(show_spinner=False)
def load_weightages() -> dict[str, list[pricing.ComponentWeightage]]:
    return pricing.load_component_weightages()


def line_rows(result: pricing.EstimateResult) -> list[dict[str, str | float]]:
    return [
        {
            "Material": line.material,
            "Unit": line.unit,
            "Quantity": round(line.quantity, 4),
            "Unit Price": money(line.unit_price),
            "Line Cost": money(line.line_cost),
        }
        for line in result.line_items
    ]


def range_line_rows(result: pricing.EstimateRangeResult) -> list[dict[str, str | float]]:
    rows = []
    upper_by_material = {line.material: line for line in result.upper.line_items}
    for lower_line in result.lower.line_items:
        upper_line = upper_by_material[lower_line.material]
        rows.append(
            {
                "Material": lower_line.material,
                "Unit": lower_line.unit,
                "Quantity": round(lower_line.quantity, 4),
                "Unit Price Range": (
                    f"{money(lower_line.unit_price)} - {money(upper_line.unit_price)}"
                ),
                "Line Cost Range": (
                    f"{money(lower_line.line_cost)} - {money(upper_line.line_cost)}"
                ),
            }
        )
    return rows


def component_rows(components: list[pricing.ComponentPrice]) -> list[dict[str, str]]:
    rows = []
    for component in components:
        if pricing.is_labor_component(component):
            coverage = "Labor rate per square"
        elif component.coverage_sqft is None:
            coverage = "Requires quantity override"
        else:
            coverage = f"{component.coverage_sqft:g} sq ft"
        rows.append(
            {
                "Material": component.material,
                "Unit": component.unit,
                "Coverage": coverage,
                "Retail Low": money(component.price.lower),
                "Retail High": money(component.price.upper),
                "Insurance": (
                    money(component.insurance_price)
                    if component.insurance_price is not None
                    else money(component.price.upper)
                ),
            }
        )
    return rows


def main() -> None:
    st.title("FPR Roof Pricing Estimator")
    st.caption("Deterministic pricing: material + labor, fixed 33% margin once, then taxes.")

    try:
        prices_by_roof = load_prices()
    except Exception as exc:
        st.error(f"Could not load pricing workbook: {exc}")
        return

    roof_types = sorted(prices_by_roof)
    if not roof_types:
        st.error("No roof types were found in the pricing workbook.")
        return

    with st.sidebar:
        st.header("Job Setup")
        roof_type = st.selectbox("Roof type", roof_types)
        pricing_mode = st.segmented_control(
            "Pricing mode",
            options=["retail", "insurance"],
            default="retail",
        )

        st.header("Roof Geometry")
        plan_area = st.number_input(
            "Plan area / horizontal roof area (sq ft)",
            min_value=1.0,
            value=2000.0,
            step=50.0,
        )
        pitch = st.text_input("Pitch", value="6:12")
        waste_factor_percent = st.number_input(
            "Waste factor (%)",
            min_value=0.0,
            value=10.0,
            step=0.5,
        )

        st.header("Labor And Taxes")
        labor_rate = st.number_input(
            "Manual labor rate override ($ / roof sq ft)",
            min_value=0.0,
            value=0.0,
            step=0.25,
        )
        st.caption("Leave 0 to use workbook Labor rows when available.")
        facet_count = st.number_input(
            "Facet count",
            min_value=1,
            value=1,
            step=1,
        )
        complexity_alpha_percent = st.number_input(
            "Complexity increase per extra facet (%)",
            min_value=0.0,
            value=2.0,
            step=0.25,
        )
        taxes = st.number_input(
            "Taxes / permits ($)",
            min_value=0.0,
            value=0.0,
            step=25.0,
        )

    components = prices_by_roof[roof_type]
    required_override_components = [
        component
        for component in components
        if component.coverage_sqft is None and not pricing.is_labor_component(component)
    ]

    st.subheader("Quantity Overrides")
    st.write(
        "Area-based components are calculated from roof area and waste. "
        "Components without area coverage need explicit quantities."
    )

    quantity_overrides: dict[str, float] = {}
    if required_override_components:
        columns = st.columns(3)
        for index, component in enumerate(required_override_components):
            with columns[index % len(columns)]:
                quantity_overrides[component.material] = st.number_input(
                    f"{component.material} ({component.unit})",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    key=f"override_{roof_type}_{component.material}",
                )
    else:
        st.info("This roof type has no required quantity overrides.")

    with st.expander("Component pricing loaded from workbook"):
        st.dataframe(component_rows(components), use_container_width=True, hide_index=True)

    calculate = st.button("Calculate Estimate", type="primary", use_container_width=True)

    if not calculate:
        return

    try:
        estimate_args = {
            "roof_type": roof_type,
            "plan_area_sqft": plan_area,
            "pitch": pitch,
            "waste_factor": waste_factor_percent / 100,
            "quantity_overrides": quantity_overrides,
            "labor_rate": labor_rate,
            "facet_count": int(facet_count),
            "taxes": taxes,
            "complexity_alpha": complexity_alpha_percent / 100,
        }
        if pricing_mode == "retail":
            result = pricing.estimate_retail_range_from_roof_area(**estimate_args)
        else:
            result = pricing.estimate_from_roof_area(
                pricing_mode="insurance",
                price_level="high",
                **estimate_args,
            )
    except Exception as exc:
        st.error(str(exc))
        return

    st.subheader("Estimate Summary")
    if isinstance(result, pricing.EstimateRangeResult):
        top_metrics = st.columns(4)
        top_metrics[0].metric(
            "Final Price Range",
            f"{money(result.lower.final_price)} - {money(result.upper.final_price)}",
        )
        top_metrics[1].metric(
            "Base Cost Range",
            f"{money(result.lower.base_cost)} - {money(result.upper.base_cost)}",
        )
        top_metrics[2].metric(
            "Material Cost Range",
            f"{money(result.lower.material_cost)} - {money(result.upper.material_cost)}",
        )
        top_metrics[3].metric("Labor Cost", money(result.lower.labor_cost))

        detail_source = result.lower
    else:
        top_metrics = st.columns(4)
        top_metrics[0].metric("Final Price", money(result.final_price))
        top_metrics[1].metric("Base Cost", money(result.base_cost))
        top_metrics[2].metric("Material Cost", money(result.material_cost))
        top_metrics[3].metric("Labor Cost", money(result.labor_cost))
        detail_source = result

    detail_metrics = st.columns(4)
    detail_metrics[0].metric("Roof Area", f"{detail_source.roof_area_sqft:,.2f} sq ft")
    detail_metrics[1].metric("Slope Factor", f"{detail_source.slope_factor:.4f}")
    detail_metrics[2].metric("Complexity", f"{detail_source.complexity_multiplier:.4f}")
    detail_metrics[3].metric("Taxes / Permits", money(detail_source.taxes))

    st.subheader("Line Items")
    if isinstance(result, pricing.EstimateRangeResult):
        st.dataframe(range_line_rows(result), use_container_width=True, hide_index=True)
    else:
        st.dataframe(line_rows(result), use_container_width=True, hide_index=True)

    st.subheader("Formula Check")
    if isinstance(result, pricing.EstimateRangeResult):
        st.code(
            (
                "Lower: "
                f"({money(result.lower.material_cost)} + {money(result.lower.labor_cost)}) "
                f"* 1.33 + {money(result.lower.taxes)} = {money(result.lower.final_price)}\n"
                "Upper: "
                f"({money(result.upper.material_cost)} + {money(result.upper.labor_cost)}) "
                f"* 1.33 + {money(result.upper.taxes)} = {money(result.upper.final_price)}"
            ),
            language="text",
        )
    else:
        st.code(
            (
                f"({money(result.material_cost)} + {money(result.labor_cost)}) "
                f"* 1.33 + {money(result.taxes)} = {money(result.final_price)}"
            ),
            language="text",
        )

    try:
        weightages = load_weightages()
        if roof_type in weightages:
            st.subheader("Cost Weightage Allocation")
            decking_option = st.radio(
                "Allocation basis",
                ["General", "With decking replacement", "Without decking replacement"],
                horizontal=True,
            )
            decking_replacement = None
            if decking_option == "With decking replacement":
                decking_replacement = True
            elif decking_option == "Without decking replacement":
                decking_replacement = False
            if isinstance(result, pricing.EstimateRangeResult):
                lower_allocation = pricing.allocate_by_weightage(
                    result.lower.final_price,
                    roof_type,
                    decking_replacement=decking_replacement,
                )
                upper_allocation = pricing.allocate_by_weightage(
                    result.upper.final_price,
                    roof_type,
                    decking_replacement=decking_replacement,
                )
                allocation = {
                    material: (lower_allocation[material], upper_allocation[material])
                    for material in lower_allocation
                }
            else:
                single_allocation = pricing.allocate_by_weightage(
                    result.final_price,
                    roof_type,
                    decking_replacement=decking_replacement,
                )
                allocation = {
                    material: (amount, amount)
                    for material, amount in single_allocation.items()
                }
            if allocation:
                st.dataframe(
                    [
                        {
                            "Material": material,
                            "Allocated Amount": (
                                money(amounts[0])
                                if amounts[0] == amounts[1]
                                else f"{money(amounts[0])} - {money(amounts[1])}"
                            ),
                        }
                        for material, amounts in allocation.items()
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
    except Exception:
        pass

    with st.expander("Raw result JSON"):
        st.json(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
