from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class QuantityContext:
    roof_area_sqft: float
    waste_factor: float
    plan_area_sqft: float
    facet_count: int
    roof_width: float
    complexity: float
    perimeter_lf: float
    ridge_lf: float
    valley_lf: float

    @property
    def waste_multiplier(self) -> float:
        return 1 + self.waste_factor


def build_quantity_context(
    roof_area_sqft: float,
    waste_factor: float,
    plan_area_sqft: float | None = None,
    facet_count: int = 1,
) -> QuantityContext:
    if roof_area_sqft <= 0:
        raise ValueError("roof_area_sqft must be greater than zero.")
    if waste_factor < 0:
        raise ValueError("waste_factor cannot be negative.")
    if facet_count <= 0:
        raise ValueError("facet_count must be greater than zero.")

    plan_area = plan_area_sqft or roof_area_sqft
    roof_width = math.sqrt(plan_area)
    complexity = 1 + 0.02 * (facet_count - 1)
    return QuantityContext(
        roof_area_sqft=roof_area_sqft,
        waste_factor=waste_factor,
        plan_area_sqft=plan_area,
        facet_count=facet_count,
        roof_width=roof_width,
        complexity=complexity,
        perimeter_lf=4 * roof_width * complexity,
        ridge_lf=roof_width * facet_count * 0.78,
        valley_lf=roof_width * 0.25 * complexity,
    )

