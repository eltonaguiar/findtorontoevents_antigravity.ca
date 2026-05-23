"""Tests for tools/adv_calibrator.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "adv_calibrator", REPO / "tools" / "adv_calibrator.py"
)
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)


class PercentileTests(unittest.TestCase):
    def test_empty_returns_zero(self) -> None:
        self.assertEqual(ac._percentile([], 50), 0.0)

    def test_single_value(self) -> None:
        self.assertEqual(ac._percentile([42.0], 50), 42.0)
        self.assertEqual(ac._percentile([42.0], 25), 42.0)

    def test_matches_numpy_linear(self) -> None:
        # numpy.percentile([1,2,3,4,5], 50) = 3.0
        self.assertAlmostEqual(ac._percentile([1, 2, 3, 4, 5], 50), 3.0)
        # numpy.percentile([1,2,3,4,5], 25) = 2.0
        self.assertAlmostEqual(ac._percentile([1, 2, 3, 4, 5], 25), 2.0)
        # numpy.percentile([1,2,3,4,5], 75) = 4.0
        self.assertAlmostEqual(ac._percentile([1, 2, 3, 4, 5], 75), 4.0)

    def test_interpolation(self) -> None:
        # numpy.percentile([1,2,3,4], 50) = 2.5
        self.assertAlmostEqual(ac._percentile([1, 2, 3, 4], 50), 2.5)


class CalibrateTests(unittest.TestCase):
    def test_empty_input(self) -> None:
        result = ac.calibrate([])
        self.assertEqual(result["by_asset_class"], {})
        self.assertEqual(result["skipped_classes"], {})

    def test_single_class_median(self) -> None:
        picks = [
            {"asset_class": "CRYPTO", "entry_price": 100.0},
            {"asset_class": "CRYPTO", "entry_price": 200.0},
            {"asset_class": "CRYPTO", "entry_price": 300.0},
            {"asset_class": "CRYPTO", "entry_price": 400.0},
            {"asset_class": "CRYPTO", "entry_price": 500.0},
        ]
        result = ac.calibrate(picks, min_n=5)
        self.assertIn("CRYPTO", result["by_asset_class"])
        c = result["by_asset_class"]["CRYPTO"]
        self.assertEqual(c["n_picks_observed"], 5)
        self.assertAlmostEqual(c["median_pick_usd"], 300.0)
        self.assertAlmostEqual(c["p25_pick_usd"], 200.0)
        self.assertAlmostEqual(c["p75_pick_usd"], 400.0)

    def test_skips_missing_entry_price(self) -> None:
        picks = [
            {"asset_class": "CRYPTO", "entry_price": 100.0},
            {"asset_class": "CRYPTO", "entry_price": None},
            {"asset_class": "CRYPTO", "entry_price": "not_a_number"},
            {"asset_class": "CRYPTO", "entry_price": 0},  # non-positive
            {"asset_class": "CRYPTO", "entry_price": -50},  # negative
            {"asset_class": "CRYPTO", "entry_price": 200.0},
            {"asset_class": "CRYPTO", "entry_price": 300.0},
            {"asset_class": "CRYPTO", "entry_price": 400.0},
            {"asset_class": "CRYPTO", "entry_price": 500.0},
        ]
        result = ac.calibrate(picks, min_n=5)
        c = result["by_asset_class"]["CRYPTO"]
        # 4 invalid + 5 valid = 5 sample
        self.assertEqual(c["n_picks_observed"], 5)
        self.assertAlmostEqual(c["median_pick_usd"], 300.0)

    def test_multi_class_grouping(self) -> None:
        picks = []
        for ep in [100.0, 200.0, 300.0, 400.0, 500.0]:
            picks.append({"asset_class": "CRYPTO", "entry_price": ep})
        for ep in [10.0, 20.0, 30.0, 40.0, 50.0]:
            picks.append({"asset_class": "EQUITY", "entry_price": ep})
        result = ac.calibrate(picks, min_n=5)
        self.assertIn("CRYPTO", result["by_asset_class"])
        self.assertIn("EQUITY", result["by_asset_class"])
        self.assertAlmostEqual(
            result["by_asset_class"]["CRYPTO"]["median_pick_usd"], 300.0)
        self.assertAlmostEqual(
            result["by_asset_class"]["EQUITY"]["median_pick_usd"], 30.0)

    def test_below_min_n_skipped(self) -> None:
        picks = [{"asset_class": "BOND", "entry_price": 100.0}]
        result = ac.calibrate(picks, min_n=5)
        self.assertNotIn("BOND", result["by_asset_class"])
        self.assertIn("BOND", result["skipped_classes"])
        self.assertEqual(result["skipped_classes"]["BOND"]["n_picks_observed"], 1)

    def test_unknown_class_label(self) -> None:
        picks = [{"entry_price": 100.0 + i} for i in range(5)]  # no asset_class
        result = ac.calibrate(picks, min_n=5)
        self.assertIn("UNKNOWN", result["by_asset_class"])

    def test_artifact_has_required_keys(self) -> None:
        picks = [{"asset_class": "CRYPTO",
                  "entry_price": 100.0 + i} for i in range(5)]
        result = ac.calibrate(picks, min_n=5)
        c = result["by_asset_class"]["CRYPTO"]
        for key in ("n_picks_observed", "min_pick_usd", "p25_pick_usd",
                    "median_pick_usd", "p75_pick_usd", "max_pick_usd"):
            self.assertIn(key, c)
        self.assertIn("last_calibrated_at", result)
        self.assertIn("schema_version", result)


if __name__ == "__main__":
    unittest.main()
