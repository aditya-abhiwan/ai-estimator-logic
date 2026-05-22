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


def field_tiles(component: Any, context: QuantityContext) -> float:
    # Unit: Per square (1 square = 100 sqft)
    return math.ceil((context.roof_area_sqft / 100) * context.waste_multiplier)


def hip_and_ridge(component: Any, context: QuantityContext) -> float:
    # Unit: Per square (100 sqft) — based on ridge linear feet
    return math.ceil((context.ridge_lf / 100) * context.waste_multiplier)


def drip_edge(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def pipe_boot_flashing(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 500))


def versa_caps(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 700))


def attic_ventilation(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 700))


def brava_starter(component: Any, context: QuantityContext) -> float:
    # Bundle = 10 pieces, each piece ~4 lf; eave perimeter
    return max(1, math.ceil(context.perimeter_lf / 40))


def step_flashing(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.ridge_lf * 0.5, 100)


def valley_metal(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.valley_lf, 50)


def cap_nails(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 2000))


def roofing_nails(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 7200))


def caulking(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 170))


def paint(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.plan_area_sqft / 1500))


def solid_tiles_for_rake_and_valley(component: Any, context: QuantityContext) -> float:
    # Bundle = 5 pieces; rake edges ~15% of perimeter + valleys
    lf = context.valley_lf + context.perimeter_lf * 0.08
    return max(1, math.ceil(lf / 5))


def decking(component: Any, context: QuantityContext) -> float:
    # Partial replacement allowance
    return max(4, math.ceil(context.plan_area_sqft / 500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "field_tiles": field_tiles,
    "hip_and_ridge": hip_and_ridge,
    "drip_edge": drip_edge,
    "pipe_boot_flashing": pipe_boot_flashing,
    "versa_caps": versa_caps,
    "attic_ventilation": attic_ventilation,
    "brava_starter": brava_starter,
    "step_flashing": step_flashing,
    "valley_metal": valley_metal,
    "cap_nails": cap_nails,
    "roofing_nails": roofing_nails,
    "caulking": caulking,
    "paint": paint,
    "solid_tiles_for_rake_and_valley": solid_tiles_for_rake_and_valley,
    "decking": decking,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)

