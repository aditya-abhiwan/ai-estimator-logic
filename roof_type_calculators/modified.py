from __future__ import annotations

import math
import re
from typing import Any

from .common import QuantityContext


def _material_key(component: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", component.material.strip().lower()).strip("_")


def _linear_quantity_for_unit(unit: str, linear_feet: float, default_lf_per_unit: float) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*linear\s*(?:feet|foot|ft)", unit.lower())
    lf_per_unit = float(match.group(1)) if match else default_lf_per_unit
    return math.ceil(linear_feet / lf_per_unit)


def modified_cap_sheet(component: Any, context: QuantityContext) -> float:
    # Roll (1 square = 100 sqft)
    return math.ceil((context.plan_area_sqft / 100) * context.waste_multiplier)


def base_sheet(component: Any, context: QuantityContext) -> float:
    # Roll (2 squares = 200 sqft)
    return math.ceil((context.plan_area_sqft / 200) * context.waste_multiplier)


def insulation_iso(component: Any, context: QuantityContext) -> float:
    # Each (32 sq ft board)
    return math.ceil((context.plan_area_sqft / 32) * context.waste_multiplier)


def modified_flashing_roll(component: Any, context: QuantityContext) -> float:
    # Roll (1 square = 100 sqft) — used at edges/penetrations
    return max(1, math.ceil(context.perimeter_lf / 100))


def asphalt_primer(component: Any, context: QuantityContext) -> float:
    # 1 bucket (5 gal) per 500 sqft
    return max(1, math.ceil(context.plan_area_sqft / 500))


def iso_plates_and_screws(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 1000))


def gravel_stop(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def pipe_boots(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 500))


def cant_strip(component: Any, context: QuantityContext) -> float:
    # Bundle (96 LF) — installed along perimeter edges
    return max(1, math.ceil(context.perimeter_lf / 96))


def termination_bar(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def sealant(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 250))


def drains(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 500))


def extra_granules(component: Any, context: QuantityContext) -> float:
    # Each (50 lbs bag) — 1 bag per 700 sqft
    return max(1, math.ceil(context.plan_area_sqft / 700))


def plastic_cement(component: Any, context: QuantityContext) -> float:
    # 1 bucket (5 gal) per 500 sqft
    return max(1, math.ceil(context.plan_area_sqft / 500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "modified_cap_sheet": modified_cap_sheet,
    "base_sheet": base_sheet,
    "insulation_iso": insulation_iso,
    "modified_flashing_roll": modified_flashing_roll,
    "asphalt_primer": asphalt_primer,
    "iso_plates_and_screws": iso_plates_and_screws,
    "gravel_stop": gravel_stop,
    "pipe_boots": pipe_boots,
    "cant_strip": cant_strip,
    "termination_bar": termination_bar,
    "sealant": sealant,
    "drains": drains,
    "extra_granules": extra_granules,
    "plastic_cement": plastic_cement,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)

