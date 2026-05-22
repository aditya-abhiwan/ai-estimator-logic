from __future__ import annotations

from typing import Any, Callable

from . import common, modified, shingles, standing_seam, stone_coated_steel, synthetic_tile_brava, tpo


QuantityCalculator = Callable[[Any, common.QuantityContext], float]


ROOF_TYPE_CALCULATORS: dict[str, QuantityCalculator] = {
    "Shingle (Class 3)": shingles.calculate_quantity,
    "Shingles (Class 4)": shingles.calculate_quantity,
    "Stone Coated Steel": stone_coated_steel.calculate_quantity,
    "Standing Seam": standing_seam.calculate_quantity,
    "Standing Seam Metal": standing_seam.calculate_quantity,
    "Synthetic Tile (Brava)": synthetic_tile_brava.calculate_quantity,
    "TPO": tpo.calculate_quantity,
    "Modified": modified.calculate_quantity,
}


def quantity_calculator_for(component: Any) -> QuantityCalculator:
    return ROOF_TYPE_CALCULATORS.get(component.roof_type, shingles.calculate_quantity)


def estimate_component_quantity(
    component: Any,
    roof_area_sqft: float,
    waste_factor: float,
    plan_area_sqft: float | None = None,
    facet_count: int = 1,
) -> float:
    context = common.build_quantity_context(
        roof_area_sqft,
        waste_factor,
        plan_area_sqft=plan_area_sqft,
        facet_count=facet_count,
    )
    return quantity_calculator_for(component)(component, context)
