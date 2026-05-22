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
    # Unit is now "Per square" (1 square = 100 sqft), apply waste factor
    return math.ceil((context.roof_area_sqft / 100) * context.waste_multiplier)


def hip_and_ridge(component: Any, context: QuantityContext) -> float:
    # 5 boxes for 12 facets -> ceil(facets * 0.4)
    return max(1, math.ceil(context.facet_count * 0.4))


def rake_trim(component: Any, context: QuantityContext) -> float:
    # 15 pieces for 12 facets -> ceil(facets * 1.25)
    return max(1, math.ceil(context.facet_count * 1.25))


def eave_trim(component: Any, context: QuantityContext) -> float:
    # 12 pieces for 2000 sqft -> eave width / 10 lf per piece
    return max(1, math.ceil(context.roof_width * 4 * 0.67 / 10))


def pipe_boot_flashing(component: Any, context: QuantityContext) -> float:
    # 4 boots for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 500))


def versa_caps(component: Any, context: QuantityContext) -> float:
    # 5 for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 400))


def attic_ventilation(component: Any, context: QuantityContext) -> float:
    # 3 for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 700))


def foam_insulation(component: Any, context: QuantityContext) -> float:
    # 25 bundles for 2236 sqft → 1 bundle ≈ 90 sqft
    return max(1, math.ceil(context.roof_area_sqft / 90))


def step_flashing(component: Any, context: QuantityContext) -> float:
    # 1 bundle for 2000 sqft, 12 facets
    return max(1, math.ceil(context.facet_count / 12))


def z_bar(component: Any, context: QuantityContext) -> float:
    # 18 pieces for 2000 sqft, 12 facets → ~1.5 per facet
    return max(1, math.ceil(context.facet_count * 1.5))


def valley_tray(component: Any, context: QuantityContext) -> float:
    # 5 trays for 2000 sqft -> valley_lf / 3
    return max(1, math.ceil(context.valley_lf / 3))


def cap_nails(component: Any, context: QuantityContext) -> float:
    # 1 box for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 2500))


def board_2x2(component: Any, context: QuantityContext) -> float:
    # 160 pieces for 2236 sqft → roof_area / 14
    return math.ceil(context.roof_area_sqft / 14)


def caulking(component: Any, context: QuantityContext) -> float:
    # 12 tubes for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 170))


def batten_1x2(component: Any, context: QuantityContext) -> float:
    # 280 pieces for 2236 sqft → roof_area / 8
    return math.ceil(context.roof_area_sqft / 8)


def screws(component: Any, context: QuantityContext) -> float:
    # 2 boxes for 2236 sqft
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def nails_for_2x2s(component: Any, context: QuantityContext) -> float:
    # 1 box for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 2500))


def granules(component: Any, context: QuantityContext) -> float:
    # 8 for 2000 sqft
    return max(1, math.ceil(context.plan_area_sqft / 250))


def decking(component: Any, context: QuantityContext) -> float:
    # Fixed allowance: 4 sheets for any roof (partial replacement)
    return max(4, math.ceil(context.plan_area_sqft / 500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "field_tiles": field_tiles,
    "hip_and_ridge": hip_and_ridge,
    "rake_trim": rake_trim,
    "eave_trim": eave_trim,
    "pipe_boot_flashing": pipe_boot_flashing,
    "versa_caps": versa_caps,
    "attic_ventilation": attic_ventilation,
    "foam_insulation": foam_insulation,
    "step_flashing": step_flashing,
    "z_bar": z_bar,
    "valley_tray": valley_tray,
    "cap_nails": cap_nails,
    "2x2_board": board_2x2,
    "caulking": caulking,
    "1x2_batten": batten_1x2,
    "screws": screws,
    "nails_for_2x2_s": nails_for_2x2s,
    "granules": granules,
    "decking": decking,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)

