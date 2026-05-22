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


def tpo_cleaner(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def iso_plates_and_screws(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def pitch_pans(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def pipe_boot_flashing(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def termination_bar(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def membrane_adhesive(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 500))


def membrane_plates_and_screws(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def corner_flashing(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 300))


def tpo_primer(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def cut_edge_sealant(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def termination_bar_sealant(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def drip_edge(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def drains(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "tpo_cleaner": tpo_cleaner,
    "iso_plates_and_screws": iso_plates_and_screws,
    "pitch_pans": pitch_pans,
    "pipe_boot_flashing": pipe_boot_flashing,
    "termination_bar": termination_bar,
    "membrane_adhesive": membrane_adhesive,
    "membrane_plates_and_screws": membrane_plates_and_screws,
    "corner_flashing": corner_flashing,
    "tpo_primer": tpo_primer,
    "cut_edge_sealant": cut_edge_sealant,
    "termination_bar_sealant": termination_bar_sealant,
    "drip_edge": drip_edge,
    "drains": drains,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)

