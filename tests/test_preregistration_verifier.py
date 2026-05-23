"""Tests for tools/preregistration_verifier.py."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "preregistration_verifier", REPO / "tools" / "preregistration_verifier.py"
)
prv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prv)


def _good_entry(**overrides) -> dict:
    base = {
        "strategy_id": "demo_strategy",
        "declared_at_utc": "2026-05-02T04:00:00Z",
        "asset_class": "CRYPTO",
        "target_metric": "wr_pct",
        "threshold": 50.0,
        "sample_size_min": 5,
        "holdout_window_start": "2026-05-01T00:00:00Z",
        "holdout_window_end": "2026-08-01T00:00:00Z",
        "git_sha_at_registration": "deadbeef" * 5,
        "schema_version": 1,
    }
    base.update(overrides)
    return base


class SchemaValidationTests(unittest.TestCase):
    def test_good_entry_is_valid(self) -> None:
        self.assertEqual(prv.validate_entry(_good_entry()), [])

    def test_missing_field(self) -> None:
        e = _good_entry()
        del e["target_metric"]
        errors = prv.validate_entry(e)
        self.assertTrue(any("target_metric" in err for err in errors))

    def test_unsupported_metric(self) -> None:
        e = _good_entry(target_metric="alpha_attribution")
        errors = prv.validate_entry(e)
        self.assertTrue(any("target_metric must be one of" in err for err in errors))

    def test_window_end_before_start(self) -> None:
        e = _good_entry(holdout_window_start="2026-08-01T00:00:00Z",
                        holdout_window_end="2026-05-01T00:00:00Z")
        errors = prv.validate_entry(e)
        self.assertTrue(any("holdout_window_end must be after" in err
                            for err in errors))

    def test_negative_threshold(self) -> None:
        e = _good_entry(threshold=-0.1)
        errors = prv.validate_entry(e)
        self.assertTrue(any("non-negative" in err for err in errors))


class HashTests(unittest.TestCase):
    def test_hash_is_deterministic(self) -> None:
        e = _good_entry()
        self.assertEqual(prv.compute_yaml_hash(e), prv.compute_yaml_hash(e))

    def test_hash_excludes_yaml_hash_field(self) -> None:
        e = _good_entry()
        h_no = prv.compute_yaml_hash(e)
        e_with = dict(e)
        e_with["yaml_hash"] = "sha256:doesnotmatter"
        self.assertEqual(h_no, prv.compute_yaml_hash(e_with))

    def test_threshold_change_flips_hash(self) -> None:
        h1 = prv.compute_yaml_hash(_good_entry(threshold=50.0))
        h2 = prv.compute_yaml_hash(_good_entry(threshold=51.0))
        self.assertNotEqual(h1, h2)


class MetricComputationTests(unittest.TestCase):
    def _picks(self, wins: int, losses: int) -> list[dict]:
        return ([{"pnl_pct": 1.0}] * wins) + ([{"pnl_pct": -1.0}] * losses)

    def test_wr_pct(self) -> None:
        m = prv.compute_metric(self._picks(7, 3), "wr_pct", "CRYPTO")
        self.assertAlmostEqual(m["value"], 70.0)

    def test_wilson_lb_pct(self) -> None:
        m = prv.compute_metric(self._picks(7, 3), "wilson_lb_wr_pct", "CRYPTO")
        self.assertGreater(m["value"], 35.0)
        self.assertLess(m["value"], 45.0)

    def test_posterior_p_above_50_high(self) -> None:
        m = prv.compute_metric(self._picks(80, 20),
                               "posterior_p_above_50", "CRYPTO")
        self.assertGreater(m["value"], 0.99)

    def test_posterior_p_above_50_low(self) -> None:
        m = prv.compute_metric(self._picks(20, 80),
                               "posterior_p_above_50", "CRYPTO")
        self.assertLess(m["value"], 0.01)

    def test_after_cost_pnl(self) -> None:
        m = prv.compute_metric(self._picks(7, 3),
                               "after_cost_pnl_per_trade", "CRYPTO")
        self.assertLessEqual(m["value"], 0.4 + 1e-9)


class WindowFilterTests(unittest.TestCase):
    def test_filters_by_strategy_class_and_window(self) -> None:
        entry = _good_entry()
        picks = [
            {"strategy": "demo_strategy", "asset_class": "CRYPTO",
             "pnl_pct": 1.0, "closed_at": "2026-06-01T00:00:00Z"},
            {"strategy": "other", "asset_class": "CRYPTO",
             "pnl_pct": 1.0, "closed_at": "2026-06-01T00:00:00Z"},
            {"strategy": "demo_strategy", "asset_class": "EQUITY",
             "pnl_pct": 1.0, "closed_at": "2026-06-01T00:00:00Z"},
            {"strategy": "demo_strategy", "asset_class": "CRYPTO",
             "pnl_pct": 1.0, "closed_at": "2026-04-01T00:00:00Z"},
            {"strategy": "demo_strategy", "asset_class": "CRYPTO",
             "pnl_pct": 1.0, "closed_at": None},
        ]
        self.assertEqual(len(prv.filter_picks_for_entry(entry, picks)), 1)


class VerifyOneEndToEndTests(unittest.TestCase):
    def test_pass_status(self) -> None:
        entry = _good_entry(target_metric="wr_pct", threshold=60.0,
                            sample_size_min=5)
        entry["yaml_hash"] = prv.compute_yaml_hash(entry)
        picks = [{"strategy": "demo_strategy", "asset_class": "CRYPTO",
                  "pnl_pct": 1.0 if i < 7 else -1.0,
                  "closed_at": "2026-06-01T00:00:00Z"} for i in range(10)]
        result = prv.verify_one(entry, picks)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["yaml_hash_ok"])
        self.assertEqual(result["n_in_window"], 10)
        self.assertAlmostEqual(result["metric_value"], 70.0)

    def test_fail_status(self) -> None:
        entry = _good_entry(target_metric="wr_pct", threshold=80.0,
                            sample_size_min=5)
        entry["yaml_hash"] = prv.compute_yaml_hash(entry)
        picks = [{"strategy": "demo_strategy", "asset_class": "CRYPTO",
                  "pnl_pct": 1.0 if i < 7 else -1.0,
                  "closed_at": "2026-06-01T00:00:00Z"} for i in range(10)]
        result = prv.verify_one(entry, picks)
        self.assertEqual(result["status"], "FAIL")

    def test_pending_status(self) -> None:
        entry = _good_entry(sample_size_min=100)
        entry["yaml_hash"] = prv.compute_yaml_hash(entry)
        picks = [{"strategy": "demo_strategy", "asset_class": "CRYPTO",
                  "pnl_pct": 1.0,
                  "closed_at": "2026-06-01T00:00:00Z"}]
        result = prv.verify_one(entry, picks)
        self.assertEqual(result["status"], "PENDING")
        self.assertIsNone(result["metric_value"])

    def test_invalid_yaml_hash_flagged(self) -> None:
        entry = _good_entry()
        entry["yaml_hash"] = "sha256:0" * 64
        picks = [{"strategy": "demo_strategy", "asset_class": "CRYPTO",
                  "pnl_pct": 1.0,
                  "closed_at": "2026-06-01T00:00:00Z"} for _ in range(10)]
        result = prv.verify_one(entry, picks)
        self.assertFalse(result["yaml_hash_ok"])

    def test_invalid_entry_returns_invalid(self) -> None:
        bad = _good_entry()
        del bad["target_metric"]
        result = prv.verify_one(bad, [])
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("target_metric" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
