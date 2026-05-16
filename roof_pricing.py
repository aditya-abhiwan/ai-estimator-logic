from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile
import xml.etree.ElementTree as ET


PRICING_WORKBOOK = Path(
    "Component Metrics AI Replacement Calculator Per Roof Material Type.xlsx"
)
WEIGHTAGE_WORKBOOK = Path(
    "Component Cost Weightage by Roof Type for Property Owner Project Plan.xlsx"
)
FIXED_MARGIN = 0.33
XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"a": XML_NS, "r": REL_NS, "rel": PKG_REL_NS}


@dataclass(frozen=True)
class PriceRange:
    lower: float
    upper: float

    def pick(self, level: str) -> float:
        if level == "low":
            return self.lower
        if level == "high":
            return self.upper
        raise ValueError("price_level must be one of: low, high")


@dataclass(frozen=True)
class ComponentPrice:
    roof_type: str
    material: str
    description: str
    unit: str
    price: PriceRange
    insurance_price: float | None = None
    coverage_sqft: float | None = None


@dataclass(frozen=True)
class ComponentWeightage:
    roof_type: str
    material: str
    with_decking_replacement: float | None
    without_decking_replacement: float | None
    percentage_of_cost: float | None
    longevity_necessity: str
    roof_health_importance: str


@dataclass(frozen=True)
class EstimateLine:
    material: str
    unit: str
    quantity: float
    unit_price: float
    line_cost: float


@dataclass(frozen=True)
class EstimateResult:
    roof_type: str
    pricing_mode: str
    price_level: str | None
    plan_area_sqft: float | None
    roof_area_sqft: float | None
    slope_factor: float | None
    material_cost: float
    labor_cost: float
    base_cost: float
    tax_amount: float
    complexity_multiplier: float
    final_price: float
    line_items: list[EstimateLine]

    @property
    def lines(self) -> list[EstimateLine]:
        return self.line_items

    def to_dict(self) -> dict[str, Any]:
        return {
            "roof_type": self.roof_type,
            "pricing_mode": self.pricing_mode,
            "price_level": self.price_level,
            "plan_area_sqft": self.plan_area_sqft,
            "roof_area_sqft": self.roof_area_sqft,
            "slope_factor": self.slope_factor,
            "material_cost": self.material_cost,
            "labor_cost": self.labor_cost,
            "base_cost": self.base_cost,
            "taxes": self.taxes,
            "complexity_multiplier": self.complexity_multiplier,
            "final_price": self.final_price,
            "line_items": [
                {
                    "material": item.material,
                    "unit": item.unit,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "line_cost": item.line_cost,
                }
                for item in self.line_items
            ],
        }


@dataclass(frozen=True)
class EstimateRangeResult:
    lower: EstimateResult
    upper: EstimateResult

    @property
    def final_price_range(self) -> tuple[float, float]:
        return self.lower.final_price, self.upper.final_price

    @property
    def material_cost_range(self) -> tuple[float, float]:
        return self.lower.material_cost, self.upper.material_cost

    @property
    def base_cost_range(self) -> tuple[float, float]:
        return self.lower.base_cost, self.upper.base_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "lower": self.lower.to_dict(),
            "upper": self.upper.to_dict(),
            "final_price_range": {
                "lower": self.lower.final_price,
                "upper": self.upper.final_price,
            },
        }


def slope_factor_from_pitch(pitch: str | float | int) -> float:
    """Return sqrt(1 + p^2), where p is rise/run."""
    if isinstance(pitch, str):
        value = pitch.strip()
        if ":" in value:
            rise, run = value.split(":", 1)
            p = float(rise) / float(run)
        else:
            p = float(value)
    else:
        p = float(pitch)
    _validate_non_negative(p, "pitch")
    return math.sqrt(1 + p**2)


def roof_area_from_plan_area(plan_area_sqft: float, pitch: str | float | int) -> float:
    return calculate_roof_area(plan_area_sqft, pitch)


def calculate_roof_area(plan_area_sqft: float, pitch: str | float | int) -> float:
    """Step 1: convert plan area into actual sloped roof area."""
    _validate_positive(plan_area_sqft, "plan_area_sqft")
    return plan_area_sqft * slope_factor_from_pitch(pitch)


def complexity_multiplier(facet_count: int, alpha: float = 0.02) -> float:
    _validate_positive(facet_count, "facet_count")
    _validate_non_negative(alpha, "alpha")
    return 1 + alpha * (facet_count - 1)


def calculate_quantities(
    components: list[ComponentPrice],
    roof_area_sqft: float,
    waste_factor: float,
    quantity_overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    """Step 2: calculate quantities from area coverage or explicit overrides."""
    _validate_positive(roof_area_sqft, "roof_area_sqft")
    _validate_non_negative(waste_factor, "waste_factor")
    overrides = {_key(k): v for k, v in (quantity_overrides or {}).items()}
    quantities: dict[str, float] = {}
    missing: list[str] = []

    for component in components:
        material_key = _key(component.material)
        if material_key in overrides:
            quantity = overrides[material_key]
            _validate_non_negative(quantity, f"quantity_overrides[{component.material}]")
            quantities[component.material] = quantity
            continue
        if component.coverage_sqft is None:
            missing.append(component.material)
            continue
        _validate_positive(component.coverage_sqft, f"coverage_sqft[{component.material}]")
        quantities[component.material] = (
            roof_area_sqft / component.coverage_sqft
        ) * (1 + waste_factor)

    if missing:
        names = ", ".join(repr(name) for name in missing)
        raise ValueError(f"Missing coverage for {names}; provide quantity overrides.")
    return quantities


def select_unit_price(
    component: ComponentPrice,
    pricing_mode: str,
    price_level: str = "low",
) -> float:
    """Step 3: select insurance or retail unit price deterministically."""
    if pricing_mode not in {"insurance", "retail"}:
        raise ValueError("pricing_mode must be one of: insurance, retail")
    if pricing_mode == "insurance":
        if component.insurance_price is not None:
            return component.insurance_price
        return component.price.upper
    return component.price.pick(price_level)


def calculate_material_cost(
    components: list[ComponentPrice],
    quantities: dict[str, float],
    pricing_mode: str,
    price_level: str = "low",
) -> tuple[float, list[EstimateLine]]:
    """Steps 4 and 5: calculate line costs and sum material cost."""
    if not quantities:
        raise ValueError("At least one component quantity is required.")
    lines: list[EstimateLine] = []

    for material, quantity in quantities.items():
        _validate_non_negative(quantity, f"quantity[{material}]")
        component = _find_component(components, material)
        unit_price = select_unit_price(component, pricing_mode, price_level)
        _validate_non_negative(unit_price, f"unit_price[{material}]")
        line_cost = quantity * unit_price
        lines.append(
            EstimateLine(
                material=component.material,
                unit=component.unit,
                quantity=quantity,
                unit_price=unit_price,
                line_cost=line_cost,
            )
        )

    return sum(line.line_cost for line in lines), lines


def calculate_labor_cost(
    labor_rate: float,
    roof_area_sqft: float,
    complexity: float,
) -> float:
    """Step 6: optional labor cost calculation."""
    _validate_non_negative(labor_rate, "labor_rate")
    _validate_positive(roof_area_sqft, "roof_area_sqft")
    _validate_positive(complexity, "complexity")
    return labor_rate * roof_area_sqft * complexity


def calculate_final_price(
    material_cost: float,
    labor_cost: float = 0,
    tax_rate: float = 0,
    margin: float = FIXED_MARGIN,
) -> dict[str, float]:
    """Step 7: apply the fixed margin once, then apply tax rate."""
    _validate_non_negative(material_cost, "material_cost")
    _validate_non_negative(labor_cost, "labor_cost")
    _validate_non_negative(tax_rate, "tax_rate")
    if margin != FIXED_MARGIN:
        raise ValueError("Margin is locked at 33% and cannot be changed.")
    base_cost = material_cost + labor_cost
    after_margin = base_cost * (1 + FIXED_MARGIN)
    tax_amount = after_margin * tax_rate
    return {
        "material_cost": material_cost,
        "labor_cost": labor_cost,
        "base_cost": base_cost,
        "tax_amount": tax_amount,
        "final_price": after_margin + tax_amount,
    }


def full_framework_price(
    material_cost: float,
    labor_cost_per_sqft: float,
    roof_area_sqft: float,
    facet_count: int = 1,
    overhead: float = 0,
    margin: float = FIXED_MARGIN,
    taxes_and_permits: float = 0,
    complexity_alpha: float = 0.02,
) -> dict[str, float]:
    """Single pricing formula: (material_cost + labor_cost) * 1.33 + taxes."""
    if overhead != 0:
        raise ValueError("Overhead multipliers are not allowed in pricing.")
    complexity = complexity_multiplier(facet_count, complexity_alpha)
    labor_cost = calculate_labor_cost(
        labor_cost_per_sqft,
        roof_area_sqft,
        complexity,
    )
    return calculate_final_price(material_cost, labor_cost, taxes_and_permits, margin)


def estimate_from_quantities(
    roof_type: str,
    quantities: dict[str, float],
    pricing_mode: str,
    price_level: str = "low",
    margin: float = FIXED_MARGIN,
    prices_path: str | Path = PRICING_WORKBOOK,
    labor_cost: float = 0,
    tax_rate: float = 0,
    roof_area_sqft: float | None = None,
) -> EstimateResult:
    """AI Estimator Logic Specification formula using explicit component quantities."""
    components = _component_lookup(load_component_prices(prices_path), roof_type)
    material_components = [
        component for component in components.values() if not is_labor_component(component)
    ]
    material_cost, lines = calculate_material_cost(
        material_components,
        quantities,
        pricing_mode,
        price_level,
    )
    # Auto-calculate labor from Excel if roof_area_sqft given and labor_cost not manually set
    if labor_cost == 0 and roof_area_sqft is not None:
        labor_component = next(
            (c for c in components.values() if is_labor_component(c)), None
        )
        if labor_component is not None:
            labor_rate = select_unit_price(labor_component, pricing_mode, price_level) / 100
            labor_cost = labor_rate * roof_area_sqft
    totals = calculate_final_price(material_cost, labor_cost, tax_rate, margin)
    return EstimateResult(
        roof_type=roof_type,
        pricing_mode=pricing_mode,
        price_level=None if pricing_mode == "insurance" else price_level,
        plan_area_sqft=None,
        roof_area_sqft=None,
        slope_factor=None,
        material_cost=totals["material_cost"],
        labor_cost=totals["labor_cost"],
        base_cost=totals["base_cost"],
        tax_amount=totals["tax_amount"],
        complexity_multiplier=1,
        final_price=totals["final_price"],
        line_items=lines,
    )


def estimate_retail_range_from_quantities(
    roof_type: str,
    quantities: dict[str, float],
    margin: float = FIXED_MARGIN,
    prices_path: str | Path = PRICING_WORKBOOK,
    labor_cost: float = 0,
    tax_rate: float = 0,
    roof_area_sqft: float | None = None,
) -> EstimateRangeResult:
    """Retail range using workbook lower and upper prices."""
    lower = estimate_from_quantities(
        roof_type=roof_type,
        quantities=quantities,
        pricing_mode="retail",
        price_level="low",
        margin=margin,
        prices_path=prices_path,
        labor_cost=labor_cost,
        tax_rate=tax_rate,
        roof_area_sqft=roof_area_sqft,
    )
    upper = estimate_from_quantities(
        roof_type=roof_type,
        quantities=quantities,
        pricing_mode="retail",
        price_level="high",
        margin=margin,
        prices_path=prices_path,
        labor_cost=labor_cost,
        tax_rate=tax_rate,
        roof_area_sqft=roof_area_sqft,
    )
    return EstimateRangeResult(lower=lower, upper=upper)


def estimate_from_roof_area(
    roof_type: str,
    plan_area_sqft: float,
    pitch: str | float | int,
    pricing_mode: str,
    price_level: str = "low",
    waste_factor: float = 0.1,
    margin: float = FIXED_MARGIN,
    quantity_overrides: dict[str, float] | None = None,
    prices_path: str | Path = PRICING_WORKBOOK,
    labor_rate: float = 0,
    facet_count: int = 1,
    tax_rate: float = 0,
    complexity_alpha: float = 0.02,
) -> EstimateResult:
    roof_area = calculate_roof_area(plan_area_sqft, pitch)
    slope_factor = slope_factor_from_pitch(pitch)
    components = _component_lookup(load_component_prices(prices_path), roof_type)
    component_list = [
        component for component in components.values() if not is_labor_component(component)
    ]
    labor_component = next(
        (component for component in components.values() if is_labor_component(component)),
        None,
    )
    quantities = calculate_quantities(
        component_list,
        roof_area,
        waste_factor,
        quantity_overrides,
    )
    material_cost, lines = calculate_material_cost(
        component_list,
        quantities,
        pricing_mode,
        price_level,
    )
    complexity = complexity_multiplier(facet_count, complexity_alpha)
    effective_labor_rate = labor_rate
    if effective_labor_rate == 0 and labor_component is not None:
        effective_labor_rate = select_unit_price(
            labor_component,
            pricing_mode,
            price_level,
        ) / 100
    labor_cost = calculate_labor_cost(effective_labor_rate, roof_area, complexity)
    totals = calculate_final_price(material_cost, labor_cost, tax_rate, margin)
    return EstimateResult(
        roof_type=roof_type,
        pricing_mode=pricing_mode,
        price_level=None if pricing_mode == "insurance" else price_level,
        plan_area_sqft=plan_area_sqft,
        roof_area_sqft=roof_area,
        slope_factor=slope_factor,
        material_cost=totals["material_cost"],
        labor_cost=totals["labor_cost"],
        base_cost=totals["base_cost"],
        tax_amount=totals["tax_amount"],
        complexity_multiplier=complexity,
        final_price=totals["final_price"],
        line_items=lines,
    )


def estimate_retail_range_from_roof_area(
    roof_type: str,
    plan_area_sqft: float,
    pitch: str | float | int,
    waste_factor: float = 0.1,
    margin: float = FIXED_MARGIN,
    quantity_overrides: dict[str, float] | None = None,
    prices_path: str | Path = PRICING_WORKBOOK,
    labor_rate: float = 0,
    facet_count: int = 1,
    tax_rate: float = 0,
    complexity_alpha: float = 0.02,
) -> EstimateRangeResult:
    """Retail estimate range using lower and upper workbook prices."""
    common_args = {
        "roof_type": roof_type,
        "plan_area_sqft": plan_area_sqft,
        "pitch": pitch,
        "pricing_mode": "retail",
        "waste_factor": waste_factor,
        "margin": margin,
        "quantity_overrides": quantity_overrides,
        "prices_path": prices_path,
        "labor_rate": labor_rate,
        "facet_count": facet_count,
        "tax_rate": tax_rate,
        "complexity_alpha": complexity_alpha,
    }
    lower = estimate_from_roof_area(price_level="low", **common_args)
    upper = estimate_from_roof_area(price_level="high", **common_args)
    return EstimateRangeResult(lower=lower, upper=upper)


def load_component_prices(
    path: str | Path = PRICING_WORKBOOK,
) -> dict[str, list[ComponentPrice]]:
    prices: dict[str, list[ComponentPrice]] = {}
    for roof_type, rows in read_xlsx(path).items():
        if not rows:
            prices[roof_type] = []
            continue
        headers = [_clean_header(value) for value in rows[0]]
        for row in rows[1:]:
            data = _row_dict(headers, row)
            material = str(data.get("material", "")).strip()
            if not material:
                continue
            price_range = _extract_price_range(data)
            if price_range is None:
                continue
            prices.setdefault(roof_type, []).append(
                ComponentPrice(
                    roof_type=roof_type,
                    material=material,
                    description=str(data.get("description", "")).strip(),
                    unit=str(data.get("unit_of_measurement", "")).strip(),
                    price=price_range,
                    insurance_price=_parse_price(
                        data.get("insurance_unit_price")
                        or data.get("insurance_price")
                    ),
                    coverage_sqft=parse_unit_coverage_sqft(
                        str(data.get("unit_of_measurement", ""))
                    ),
                )
            )
    return prices


def load_component_weightages(
    path: str | Path = WEIGHTAGE_WORKBOOK,
) -> dict[str, list[ComponentWeightage]]:
    weightages: dict[str, list[ComponentWeightage]] = {}
    for roof_type, rows in read_xlsx(path).items():
        if not rows:
            weightages[roof_type] = []
            continue
        headers = [_clean_header(value) for value in rows[0]]
        for row in rows[1:]:
            data = _row_dict(headers, row)
            material = str(data.get("material", "")).strip()
            if not material:
                continue
            weightages.setdefault(roof_type, []).append(
                ComponentWeightage(
                    roof_type=roof_type,
                    material=material,
                    with_decking_replacement=_parse_percent(
                        data.get("percentage_of_cost_with_decking_replacement")
                    ),
                    without_decking_replacement=_parse_percent(
                        data.get("percentage_of_cost_without_decking_replacement")
                    ),
                    percentage_of_cost=_parse_percent(data.get("percentage_of_cost")),
                    longevity_necessity=str(data.get("longevity_necessity", "")).strip(),
                    roof_health_importance=str(
                        data.get("importance_for_overall_roof_health_scale_1_5")
                        or data.get("importance_for_overall_roof_health_scale_1_3")
                        or ""
                    ).strip(),
                )
            )
    return weightages


def allocate_by_weightage(
    total_price: float,
    roof_type: str,
    decking_replacement: bool | None = None,
    weightages_path: str | Path = WEIGHTAGE_WORKBOOK,
) -> dict[str, float]:
    _validate_non_negative(total_price, "total_price")
    by_roof = load_component_weightages(weightages_path)
    if roof_type not in by_roof:
        available = ", ".join(sorted(by_roof))
        raise ValueError(f"Unknown roof_type {roof_type!r}. Available: {available}")

    allocation: dict[str, float] = {}
    for item in by_roof[roof_type]:
        if decking_replacement is True:
            percentage = item.with_decking_replacement
        elif decking_replacement is False:
            percentage = item.without_decking_replacement
        else:
            percentage = item.percentage_of_cost
        if percentage is not None:
            allocation[item.material] = total_price * percentage
    return allocation


def read_xlsx(path: str | Path) -> dict[str, list[list[Any]]]:
    """Minimal XLSX reader for cell values; avoids external package requirements."""
    path = Path(path)
    with ZipFile(path) as archive:
        shared_strings = _load_shared_strings(archive)
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            rel.get("Id"): rel.get("Target")
            for rel in rels.findall("rel:Relationship", NS)
        }

        sheets: dict[str, list[list[Any]]] = {}
        for sheet in workbook.findall("a:sheets/a:sheet", NS):
            name = sheet.get("name", "")
            relation_id = sheet.get(f"{{{REL_NS}}}id")
            target = relationship_targets[relation_id]
            sheet_path = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
            root = ET.fromstring(archive.read(sheet_path))
            sheets[name] = _read_sheet_rows(root, shared_strings)
        return sheets


def parse_unit_coverage_sqft(unit: str) -> float | None:
    text = unit.lower()
    if "linear" in text:
        return None
    sqft_match = re.search(r"(\d+(?:\.\d+)?)\s*sq\s*ft", text)
    if sqft_match:
        return float(sqft_match.group(1))
    square_match = re.search(r"(\d+(?:\.\d+)?)\s*squares?", text)
    if square_match:
        return float(square_match.group(1)) * 100
    return None


def is_labor_component(component: ComponentPrice) -> bool:
    material = component.material.strip().lower()
    return material in {"labor", "labour"}


def print_estimate(result: EstimateResult) -> None:
    if result.plan_area_sqft is not None:
        print(f"Roof type: {result.roof_type}")
        print(f"Plan area: {result.plan_area_sqft:.2f} sq ft")
        print(f"Slope factor: {result.slope_factor:.4f}")
        print(f"Roof area: {result.roof_area_sqft:.2f} sq ft")
    print(f"Pricing mode: {result.pricing_mode}")
    if result.price_level:
        print(f"Price level: {result.price_level}")
    print("")
    print("Lines:")
    for line in result.line_items:
        print(
            f"- {line.material}: {line.quantity:.4f} x "
            f"${line.unit_price:.2f} = ${line.line_cost:.2f} ({line.unit})"
        )
    print("")
    print(f"Material cost: ${result.material_cost:.2f}")
    print(f"Labor cost: ${result.labor_cost:.2f}")
    print(f"Taxes/permits: ${result.taxes:.2f}")
    print(f"Complexity multiplier: {result.complexity_multiplier:.4f}")
    print(f"Base cost: ${result.base_cost:.2f}")
    print(f"Final price with 33% margin: ${result.final_price:.2f}")


def print_estimate_range(result: EstimateRangeResult) -> None:
    print_estimate(result.lower)
    print("")
    print("Retail upper estimate:")
    for line in result.upper.line_items:
        print(
            f"- {line.material}: {line.quantity:.4f} x "
            f"${line.unit_price:.2f} = ${line.line_cost:.2f} ({line.unit})"
        )
    print("")
    print(
        "Retail final price range: "
        f"${result.lower.final_price:.2f} - ${result.upper.final_price:.2f}"
    )


def parse_quantity_overrides(values: list[str]) -> dict[str, float]:
    overrides: dict[str, float] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(
                "Quantity overrides must use MATERIAL=QUANTITY, "
                "for example: 'Drip Edge=20'"
            )
        material, quantity = value.split("=", 1)
        material = material.strip()
        if not material:
            raise ValueError("Quantity override material cannot be blank.")
        overrides[material] = float(quantity)
    return overrides


def _load_shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall("a:si", NS):
        strings.append("".join(text.text or "" for text in item.findall(".//a:t", NS)))
    return strings


def _read_sheet_rows(root: ET.Element, shared_strings: list[str]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for row in root.findall("a:sheetData/a:row", NS):
        values: list[Any] = []
        for cell in row.findall("a:c", NS):
            column_index = _column_number(cell.get("r", "")) - 1
            while len(values) < column_index:
                values.append("")
            values.append(_cell_value(cell, shared_strings))
        while values and values[-1] == "":
            values.pop()
        rows.append(values)
    return rows


def _column_number(cell_reference: str) -> int:
    match = re.match(r"([A-Z]+)", cell_reference)
    if not match:
        return 1
    number = 0
    for letter in match.group(1):
        number = number * 26 + ord(letter) - 64
    return number


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//a:t", NS))
    value = cell.find("a:v", NS)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    if cell_type == "b":
        return value.text == "1"
    try:
        number = float(value.text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value.text


def _clean_header(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _row_dict(headers: list[str], row: list[Any]) -> dict[str, Any]:
    return {headers[index]: row[index] if index < len(row) else "" for index in range(len(headers))}


def _extract_price_range(values: dict[str, Any]) -> PriceRange | None:
    lower = _parse_price(values.get("price_per_unit_lower"))
    upper = _parse_price(values.get("price_per_unit_upper"))
    text_range = _parse_price_range_text(values.get("price_per_unit"))

    if lower is not None and upper is not None:
        return PriceRange(lower=lower, upper=upper)
    if text_range is not None:
        return text_range
    if lower is not None:
        return PriceRange(lower=lower, upper=lower)
    if upper is not None:
        return PriceRange(lower=upper, upper=upper)
    return None


def _parse_price(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None or str(value).strip() == "":
        return None
    match = re.search(r"\d+(?:,\d{3})*(?:\.\d+)?", str(value).replace("$", ""))
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def _parse_price_range_text(value: Any) -> PriceRange | None:
    if isinstance(value, (int, float)):
        number = float(value)
        return PriceRange(number, number)
    if value is None:
        return None
    numbers = [
        float(item.replace(",", ""))
        for item in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", str(value))
    ]
    if len(numbers) >= 2:
        return PriceRange(numbers[0], numbers[1])
    return None


def _parse_percent(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 100 if number >= 1 else number
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip().lower()
    if "less than 1" in text:
        return 0.005
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    number = float(match.group(0))
    return number / 100 if "%" in text or number > 1 else number


def _component_lookup(
    prices_by_roof_type: dict[str, list[ComponentPrice]],
    roof_type: str,
) -> dict[str, ComponentPrice]:
    if roof_type not in prices_by_roof_type:
        available = ", ".join(sorted(prices_by_roof_type))
        raise ValueError(f"Unknown roof_type {roof_type!r}. Available: {available}")
    return {_key(component.material): component for component in prices_by_roof_type[roof_type]}


def _find_component(
    components: list[ComponentPrice],
    material: str,
) -> ComponentPrice:
    material_key = _key(material)
    for component in components:
        if _key(component.material) == material_key:
            return component
    available = ", ".join(component.material for component in components)
    raise ValueError(f"Unknown material {material!r}. Available for this roof type: {available}")


def _validate_positive(value: float, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Calculate roof replacement estimates.")
    parser.add_argument("--roof-type", default="Shingle (Class 3)")
    parser.add_argument("--plan-area", type=float, default=2000)
    parser.add_argument("--pitch", default="6:12")
    parser.add_argument(
        "--pricing-mode",
        choices=("insurance", "retail"),
        default="retail",
    )
    parser.add_argument(
        "--price-level",
        choices=("low", "high"),
        default="low",
        help="Only used for insurance fallback or forced single retail estimate.",
    )
    parser.add_argument(
        "--single-retail-estimate",
        action="store_true",
        help="Return only --price-level for retail instead of the full lower-upper range.",
    )
    parser.add_argument("--waste-factor", type=float, default=0.1)
    parser.add_argument("--labor-rate", type=float, default=0)
    parser.add_argument("--facet-count", type=int, default=1)
    parser.add_argument("--taxes", type=float, default=0)
    parser.add_argument("--complexity-alpha", type=float, default=0.02)
    parser.add_argument(
        "--quantity-override",
        action="append",
        default=[],
        metavar="MATERIAL=QUANTITY",
        help="Provide non-area component quantities. Repeat this option as needed.",
    )
    args = parser.parse_args()

    estimate_args = {
        "roof_type": args.roof_type,
        "plan_area_sqft": args.plan_area,
        "pitch": args.pitch,
        "waste_factor": args.waste_factor,
        "quantity_overrides": parse_quantity_overrides(args.quantity_override),
        "labor_rate": args.labor_rate,
        "facet_count": args.facet_count,
        "taxes": args.taxes,
        "complexity_alpha": args.complexity_alpha,
    }
    if args.pricing_mode == "retail" and not args.single_retail_estimate:
        print_estimate_range(estimate_retail_range_from_roof_area(**estimate_args))
    else:
        result = estimate_from_roof_area(
            pricing_mode=args.pricing_mode,
            price_level=args.price_level,
            **estimate_args,
        )
        print_estimate(result)


if __name__ == "__main__":
    main()
