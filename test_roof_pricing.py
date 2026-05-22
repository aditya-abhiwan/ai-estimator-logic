import math
import unittest

import roof_type_calculators as calculators
from roof_type_calculators import shingles, stone_coated_steel
import roof_pricing as pricing


class RoofPricingModelTests(unittest.TestCase):
    def test_roof_area_uses_pitch_slope_factor(self):
        self.assertAlmostEqual(
            pricing.slope_factor_from_pitch("6:12"),
            math.sqrt(1 + 0.5**2),
        )
        self.assertAlmostEqual(
            pricing.calculate_roof_area(2000, "6:12"),
            2000 * math.sqrt(1 + 0.5**2),
        )

    def test_final_price_applies_fixed_margin_once_then_taxes(self):
        totals = pricing.calculate_final_price(
            material_cost=1000,
            labor_cost=200,
            tax_rate=0.05,  # 5% tax rate
        )

        self.assertEqual(totals["base_cost"], 1200)
        expected_tax_amount = 1200 * 1.33 * 0.05
        self.assertEqual(totals["tax_amount"], expected_tax_amount)
        self.assertEqual(totals["final_price"], 1200 * 1.33 + expected_tax_amount)

    def test_tax_rate_applies_only_to_residential_property(self):
        totals = pricing.calculate_final_price(
            material_cost=1000,
            tax_rate=0.05,
            is_residential_property=False,
        )

        self.assertEqual(totals["tax_rate"], 0)
        self.assertEqual(totals["tax_amount"], 0)
        self.assertEqual(totals["final_price"], 1000 * 1.33)

    def test_margin_cannot_be_changed(self):
        with self.assertRaisesRegex(ValueError, "Margin is locked"):
            pricing.calculate_final_price(1000, margin=0.25)

    def test_rejects_overhead_multiplier(self):
        with self.assertRaisesRegex(ValueError, "Overhead multipliers"):
            pricing.full_framework_price(
                material_cost=1000,
                labor_cost_per_sqft=1,
                roof_area_sqft=100,
                overhead=0.1,
            )

    def test_retail_price_levels_use_lower_and_upper_only(self):
        price_range = pricing.PriceRange(lower=10, upper=20)

        self.assertEqual(price_range.pick("low"), 10)
        self.assertEqual(price_range.pick("high"), 20)
        with self.assertRaisesRegex(ValueError, "low, high"):
            price_range.pick("likely")

    def test_retail_range_uses_lower_and_upper_prices(self):
        quantities = {"Field Shingles": 1}
        result = pricing.estimate_retail_range_from_quantities(
            "Shingle (Class 3)",
            quantities,
        )

        self.assertLess(result.lower.final_price, result.upper.final_price)
        self.assertEqual(result.lower.price_level, "low")
        self.assertEqual(result.upper.price_level, "high")

    def test_estimate_to_dict_includes_tax_fields(self):
        result = pricing.estimate_from_quantities(
            "Shingle (Class 3)",
            {"Field Shingles": 1},
            "retail",
            tax_rate=0.05,
        )

        data = result.to_dict()
        self.assertIn("tax_amount", data)
        self.assertEqual(data["tax_rate"], 0.05)
        self.assertTrue(data["is_residential_property"])
        self.assertIn("calculation_log", data)
        self.assertTrue(any("Final price" in item for item in data["calculation_log"]))

    def test_roof_area_estimate_includes_step_by_step_log(self):
        result = pricing.estimate_from_roof_area(
            "TPO",
            plan_area_sqft=1000,
            pitch="0:12",
            pricing_mode="retail",
            waste_factor=0,
            tax_rate=0.05,
        )

        log_text = "\n".join(result.calculation_log)
        self.assertIn("1. Geometry", log_text)
        self.assertIn("2. Quantities And Line Costs", log_text)
        self.assertIn("After fixed 33% margin", log_text)

    def test_workbook_labor_row_becomes_labor_cost_for_tpo(self):
        result = pricing.estimate_retail_range_from_roof_area(
            "TPO",
            plan_area_sqft=1000,
            pitch="0:12",
            waste_factor=0,
        )

        self.assertEqual(result.lower.labor_cost, 1500)
        self.assertEqual(result.upper.labor_cost, 2000)
        self.assertTrue(
            all(line.material != "Labor" for line in result.lower.line_items)
        )

    def test_missing_coverage_components_are_calculated(self):
        components = [
            pricing.ComponentPrice(
                roof_type="Example",
                material="Area Material",
                description="",
                unit="Square (100 sq ft)",
                price=pricing.PriceRange(1, 1),
                coverage_sqft=100,
            ),
            pricing.ComponentPrice(
                roof_type="Example",
                material="Count Material",
                description="",
                unit="Each",
                price=pricing.PriceRange(1, 1),
                coverage_sqft=None,
            ),
        ]

        quantities = pricing.calculate_quantities(
            components,
            roof_area_sqft=1000,
            waste_factor=0.1,
        )

        self.assertEqual(quantities["Area Material"], 11)
        self.assertEqual(quantities["Count Material"], 1)

    def test_roof_type_quantity_calculators_are_used(self):
        field_tiles = pricing.ComponentPrice(
            roof_type="Stone Coated Steel",
            material="Field Tiles",
            description="",
            unit="Each",
            price=pricing.PriceRange(1, 1),
        )
        decking = pricing.ComponentPrice(
            roof_type="Stone Coated Steel",
            material="Decking",
            description="",
            unit="Each",
            price=pricing.PriceRange(1, 1),
        )
        drip_edge = pricing.ComponentPrice(
            roof_type="Shingle (Class 3)",
            material="Drip Edge",
            description="",
            unit="Each (10 Linear Feet)",
            price=pricing.PriceRange(1, 1),
        )

        self.assertEqual(
            calculators.quantity_calculator_for(field_tiles),
            stone_coated_steel.calculate_quantity,
        )
        self.assertEqual(
            calculators.quantity_calculator_for(decking),
            stone_coated_steel.calculate_quantity,
        )
        self.assertEqual(
            calculators.quantity_calculator_for(drip_edge),
            shingles.calculate_quantity,
        )

    def test_roof_pricing_uses_roof_type_calculator_package(self):
        self.assertIs(
            pricing.estimate_component_quantity,
            calculators.estimate_component_quantity,
        )

    def test_stone_coated_steel_quantities_are_not_zero(self):
        result = pricing.estimate_from_roof_area(
            "Stone Coated Steel",
            plan_area_sqft=3403,
            pitch="4:12",
            pricing_mode="retail",
            labor_rate=2,
            facet_count=14,
        )

        quantities = {line.material: line.quantity for line in result.line_items}
        self.assertGreater(quantities["Field Tiles"], 0)
        self.assertGreater(quantities["Decking"], 0)

    def test_workbook_prices_load_roof_types(self):
        roof_types = pricing.load_component_prices()

        self.assertIn("Shingle (Class 3)", roof_types)
        self.assertIn("TPO", roof_types)
        self.assertGreater(len(roof_types["TPO"]), 1)

    def test_standing_seam_uses_per_square_quantities_and_price_range(self):
        prices = pricing.load_component_prices()
        standing_seam = {
            component.material: component
            for component in prices["Standing Seam"]
        }

        self.assertEqual(standing_seam["Material and Labor"].price.lower, 680)
        self.assertEqual(standing_seam["Material and Labor"].price.upper, 730)

        result = pricing.estimate_retail_range_from_roof_area(
            "Standing Seam",
            plan_area_sqft=2000,
            pitch="6:12",
            waste_factor=0.1,
        )

        lower_quantities = {
            line.material: line.quantity
            for line in result.lower.line_items
        }
        self.assertAlmostEqual(
            lower_quantities["Material and Labor"],
            (pricing.calculate_roof_area(2000, "6:12") / 100) * 1.1,
        )
        self.assertAlmostEqual(
            lower_quantities["Tear Off"],
            pricing.calculate_roof_area(2000, "6:12") / 100,
        )
        self.assertEqual(lower_quantities["Decking"], 4)


if __name__ == "__main__":
    unittest.main()
