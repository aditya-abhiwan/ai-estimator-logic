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


def hip_and_ridge_shingles(component: Any, context: QuantityContext) -> float:
    # 15 bundles @ 33 lf = 495 lf for 2000 sqft, 12 facets → ridge_lf = facet_count * roof_width * 0.9
    hip_ridge_lf = context.roof_width * (1 + context.facet_count * 0.25)
    return _linear_quantity_for_unit(component.unit, hip_ridge_lf, 33)


def drip_edge(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def starter(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 120)


def valley_metal(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.valley_lf, 50)


def step_flashing(component: Any, context: QuantityContext) -> float:
    # 1 bundle for 2000 sqft, 12 facets
    return max(1, math.ceil(context.facet_count / 15))


def ice_and_water_underlayment(component: Any, context: QuantityContext) -> float:
    # Only eaves + valleys, ~15% of plan area → 3 rolls for 2000 sqft
    eaves_sqft = context.plan_area_sqft * 0.15
    return max(1, math.ceil(eaves_sqft / 100))


def pipe_boot_flashing(component: Any, context: QuantityContext) -> float:
    # 4 boots for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 500))


def versa_caps(component: Any, context: QuantityContext) -> float:
    # 4-6 for 2000 sqft → use midpoint ~5
    return max(1, math.ceil(context.plan_area_sqft / 650))


def attic_ventilation(component: Any, context: QuantityContext) -> float:
    # 3 vents for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 700))


def cap_nails(component: Any, context: QuantityContext) -> float:
    # 1 box for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 2500))


def roofing_nails(component: Any, context: QuantityContext) -> float:
    # 2 boxes for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 2500))


def caulking(component: Any, context: QuantityContext) -> float:
    # 8 tubes for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 250))


def paint(component: Any, context: QuantityContext) -> float:
    # 1-2 for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 1500))


def decking(component: Any, context: QuantityContext) -> float:
    # Fixed allowance: 4 sheets for any roof (partial replacement)
    return max(4, math.ceil(context.plan_area_sqft / 500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "hip_and_ridge_shingles": hip_and_ridge_shingles,
    "drip_edge": drip_edge,
    "starter": starter,
    "valley_metal": valley_metal,
    "step_flashing": step_flashing,
    "ice_and_water_underlayment": ice_and_water_underlayment,
    "pipe_boot_flashing": pipe_boot_flashing,
    "versa_caps": versa_caps,
    "attic_ventilation": attic_ventilation,
    "cap_nails": cap_nails,
    "roofing_nails": roofing_nails,
    "caulking": caulking,
    "paint": paint,
    "decking": decking,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)
