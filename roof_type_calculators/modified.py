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


def asphalt_primer(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def iso_plates_and_screws(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def gravel_stop(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def pipe_boots(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def cant_strip(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.valley_lf, 96)


def termination_bar(component: Any, context: QuantityContext) -> float:
    return _linear_quantity_for_unit(component.unit, context.perimeter_lf, 10)


def sealant(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def drains(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1500))


def extra_granules(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def plastic_cement(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
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

