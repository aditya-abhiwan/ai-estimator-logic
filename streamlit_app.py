from __future__ import annotations

import io
import json

import streamlit as st
from fpdf import FPDF

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
            coverage = "Calculated by estimator"
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
    st.caption(
        "Deterministic pricing: material + labor, fixed 33% margin once, "
        "then residential tax percentage."
    )

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
        property_type = st.segmented_control(
            "Property type",
            options=["residential", "commercial"],
            default="residential",
        )
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
        tax_percent = st.number_input(
            "Residential tax rate (%)",
            min_value=0.0,
            value=0.0,
            step=0.5,
        )
        if property_type != "residential":
            st.caption("Tax percentage is ignored for non-residential properties.")

    components = prices_by_roof[roof_type]

    with st.expander("Component pricing loaded from workbook"):
        st.dataframe(component_rows(components), width="stretch", hide_index=True)

    calculate = st.button("Calculate Estimate", type="primary", width="stretch")

    if calculate:
        try:
            estimate_args = {
                "roof_type": roof_type,
                "plan_area_sqft": plan_area,
                "pitch": pitch,
                "waste_factor": waste_factor_percent / 100,
                "facet_count": int(facet_count),
                "tax_rate": tax_percent / 100,
                "is_residential_property": property_type == "residential",
                "complexity_alpha": complexity_alpha_percent / 100,
            }
            if pricing_mode == "retail":
                st.session_state["result"] = pricing.estimate_retail_range_from_roof_area(**estimate_args)
            else:
                st.session_state["result"] = pricing.estimate_from_roof_area(
                    pricing_mode="insurance",
                    price_level="high",
                    **estimate_args,
                )
        except Exception as exc:
            st.error(str(exc))
            return

    if "result" not in st.session_state:
        return

    result = st.session_state["result"]

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
    detail_metrics[3].metric("Tax Amount", money(detail_source.tax_amount))

    effective_tax_rate = detail_source.tax_rate
    st.download_button(
        label="⬇ Download Report (PDF)",
        data=generate_pdf_report(
            result, detail_source, effective_tax_rate,
            plan_area=plan_area, pitch=pitch,
            facet_count=int(facet_count),
            waste_factor_percent=waste_factor_percent,
            roof_type=roof_type,
        ),
        file_name=f"roof_estimate_{roof_type.replace(' ', '_')}_{int(plan_area)}sqft.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.subheader("Line Items")
    if isinstance(result, pricing.EstimateRangeResult):
        st.dataframe(range_line_rows(result), width="stretch", hide_index=True)
    else:
        st.dataframe(line_rows(result), width="stretch", hide_index=True)

    st.subheader("Formula Check")
    if isinstance(result, pricing.EstimateRangeResult):
        st.code(
            (
                "Lower: "
                f"({money(result.lower.material_cost)} + {money(result.lower.labor_cost)}) "
                f"* 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.lower.final_price)}\n"
                "Upper: "
                f"({money(result.upper.material_cost)} + {money(result.upper.labor_cost)}) "
                f"* 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.upper.final_price)}"
            ),
            language="text",
        )
    else:
        st.code(
            (
                f"({money(result.material_cost)} + {money(result.labor_cost)}) "
                f"* 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.final_price)}"
            ),
            language="text",
        )

    with st.expander("Calculation Logs", expanded=True):
        if isinstance(result, pricing.EstimateRangeResult):
            low_tab, high_tab = st.tabs(["Retail Low", "Retail High"])
            with low_tab:
                st.code("\n".join(result.lower.calculation_log), language="text")
            with high_tab:
                st.code("\n".join(result.upper.calculation_log), language="text")
        else:
            st.code("\n".join(result.calculation_log), language="text")

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
                    width="stretch",
                    hide_index=True,
                )
    except Exception:
        pass

    with st.expander("Raw result JSON"):
        st.json(json.dumps(result.to_dict(), indent=2))


def generate_pdf_report(
    result: pricing.EstimateRangeResult | pricing.EstimateResult,
    detail_source: pricing.EstimateResult,
    effective_tax_rate: float,
    plan_area: float = 0,
    pitch: str = "",
    facet_count: int = 1,
    waste_factor_percent: float = 0,
    roof_type: str = "",
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "FPR Roof Pricing Estimate Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Job Inputs ───────────────────────────────────────────────────────────
    _section(pdf, "Job Inputs")
    _kv_table(pdf, [
        ("Roof Type",          roof_type),
        ("Plan Area (sq ft)",  f"{plan_area:,.2f}"),
        ("Pitch",              pitch),
        ("Facet Count",        str(facet_count)),
        ("Waste Factor",       f"{waste_factor_percent:.1f}%"),
    ])

    # ── 1. Estimate Summary ──────────────────────────────────────────────────
    _section(pdf, "1. Estimate Summary")
    if isinstance(result, pricing.EstimateRangeResult):
        rows = [
            ("Final Price Range", f"{money(result.lower.final_price)} - {money(result.upper.final_price)}"),
            ("Base Cost Range",   f"{money(result.lower.base_cost)}  - {money(result.upper.base_cost)}"),
            ("Material Cost Range", f"{money(result.lower.material_cost)} - {money(result.upper.material_cost)}"),
            ("Labor Cost",        money(result.lower.labor_cost)),
        ]
    else:
        rows = [
            ("Final Price",    money(result.final_price)),
            ("Base Cost",      money(result.base_cost)),
            ("Material Cost",  money(result.material_cost)),
            ("Labor Cost",     money(result.labor_cost)),
        ]
    rows += [
        ("Roof Area",          f"{detail_source.roof_area_sqft:,.2f} sq ft"),
        ("Slope Factor",       f"{detail_source.slope_factor:.4f}"),
        ("Complexity",         f"{detail_source.complexity_multiplier:.4f}"),
        ("Tax Amount",         money(detail_source.tax_amount)),
    ]
    _kv_table(pdf, rows)

    # ── 2. Line Items ────────────────────────────────────────────────────────
    _section(pdf, "2. Line Items")
    if isinstance(result, pricing.EstimateRangeResult):
        headers = ["Material", "Unit", "Qty", "Unit Price Range", "Line Cost Range"]
        data = [
            [r["Material"], r["Unit"], str(r["Quantity"]), r["Unit Price Range"], r["Line Cost Range"]]
            for r in range_line_rows(result)
        ]
    else:
        headers = ["Material", "Unit", "Qty", "Unit Price", "Line Cost"]
        data = [
            [r["Material"], r["Unit"], str(r["Quantity"]), r["Unit Price"], r["Line Cost"]]
            for r in line_rows(result)
        ]
    _table(pdf, headers, data)

    # ── 3. Formula Check ─────────────────────────────────────────────────────
    _section(pdf, "3. Formula Check")
    if isinstance(result, pricing.EstimateRangeResult):
        formula = (
            f"Lower: ({money(result.lower.material_cost)} + {money(result.lower.labor_cost)})"
            f" * 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.lower.final_price)}\n"
            f"Upper: ({money(result.upper.material_cost)} + {money(result.upper.labor_cost)})"
            f" * 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.upper.final_price)}"
        )
    else:
        formula = (
            f"({money(result.material_cost)} + {money(result.labor_cost)})"
            f" * 1.33 * (1 + {effective_tax_rate:.2%}) = {money(result.final_price)}"
        )
    pdf.set_font("Courier", size=9)
    pdf.multi_cell(0, 6, formula)
    pdf.ln(2)

    # ── 4. Calculation Logs ──────────────────────────────────────────────────
    _section(pdf, "4. Calculation Logs")
    pdf.set_font("Courier", size=8)
    if isinstance(result, pricing.EstimateRangeResult):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Retail Low:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", size=8)
        pdf.multi_cell(0, 5, "\n".join(result.lower.calculation_log))
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, "Retail High:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Courier", size=8)
        pdf.multi_cell(0, 5, "\n".join(result.upper.calculation_log))
    else:
        pdf.multi_cell(0, 5, "\n".join(result.calculation_log))

    buf = io.BytesIO()
    buf.write(pdf.output())
    return buf.getvalue()


def _section(pdf: FPDF, title: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _kv_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    pdf.set_font("Helvetica", size=9)
    for label, value in rows:
        pdf.cell(70, 6, label, border=1)
        pdf.cell(0, 6, value, border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)


def _table(pdf: FPDF, headers: list[str], rows: list[list[str]]) -> None:
    col_w = pdf.epw / len(headers)
    pdf.set_font("Helvetica", "B", 8)
    for h in headers:
        pdf.cell(col_w, 6, h, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", size=8)
    for row in rows:
        for cell in row:
            pdf.cell(col_w, 6, str(cell), border=1)
        pdf.ln()
    pdf.ln(4)


if __name__ == "__main__":
    main()
