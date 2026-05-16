import math
import unittest

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

    def test_workbook_labor_row_becomes_labor_cost_for_tpo(self):
        components = pricing.load_component_prices()["TPO"]
        overrides = {
            component.material: 0
            for component in components
            if component.coverage_sqft is None
            and not pricing.is_labor_component(component)
        }

        result = pricing.estimate_retail_range_from_roof_area(
            "TPO",
            plan_area_sqft=1000,
            pitch="0:12",
            waste_factor=0,
            quantity_overrides=overrides,
        )

        self.assertEqual(result.lower.labor_cost, 1500)
        self.assertEqual(result.upper.labor_cost, 2000)
        self.assertTrue(
            all(line.material != "Labor" for line in result.lower.line_items)
        )

    def test_quantity_overrides_do_not_apply_waste(self):
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
            quantity_overrides={"Count Material": 3},
        )

        self.assertEqual(quantities["Area Material"], 11)
        self.assertEqual(quantities["Count Material"], 3)

    def test_workbook_prices_load_roof_types(self):
        roof_types = pricing.load_component_prices()

        self.assertIn("Shingle (Class 3)", roof_types)
        self.assertIn("TPO", roof_types)
        self.assertGreater(len(roof_types["TPO"]), 1)


if __name__ == "__main__":
    unittest.main()
