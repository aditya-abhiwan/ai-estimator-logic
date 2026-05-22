from __future__ import annotations

import math
import re
from typing import Any

from .common import QuantityContext


def _material_key(component: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", component.material.strip().lower()).strip("_")


def material_and_labor(component: Any, context: QuantityContext) -> float:
    return (context.roof_area_sqft / 100) * context.waste_multiplier


def tear_off(component: Any, context: QuantityContext) -> float:
    return context.roof_area_sqft / 100


def decking(component: Any, context: QuantityContext) -> float:
    return max(4, math.ceil(context.plan_area_sqft / 500))


def default_quantity(component: Any, context: QuantityContext) -> float:
    return max(1, math.ceil(context.roof_area_sqft / 1000))


CALCULATORS = {
    "material_and_labor": material_and_labor,
    "tear_off": tear_off,
    "decking": decking,
}


def calculate_quantity(component: Any, context: QuantityContext) -> float:
    return CALCULATORS.get(_material_key(component), default_quantity)(component, context)
