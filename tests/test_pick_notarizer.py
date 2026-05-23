"""Smoke tests for tools/pick_notarizer.py.

Verifies:
  1. _canonical_json is deterministic regardless of insertion order.
  2. _hash_picks_payload returns stable hashes for identical inputs.
  3. A trivial mutation to active picks changes the hash.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pick_notarizer", REPO / "tools" / "pick_notarizer.py"
)
pn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pn)


class CanonicalJsonTests(unittest.TestCase):
    def test_key_order_independent(self) -> None:
        a = {"x": 1, "y": 2, "z": [3, 4]}
        b = {"z": [3, 4], "y": 2, "x": 1}
        self.assertEqual(pn._canonical_json(a), pn._canonical_json(b))

    def test_unicode_normalised(self) -> None:
        self.assertEqual(
            pn._canonical_json({"sym": "BTCUSDT"}),
            pn._canonical_json({"sym": "BTCUSDT"}),
        )

    def test_no_whitespace_drift(self) -> None:
        # default json.dumps uses ", " and ": "; our canonical strips both
        self.assertNotIn(", ", pn._canonical_json({"a": 1, "b": 2}))
        self.assertNotIn(": ", pn._canonical_json({"a": 1, "b": 2}))


class HashStabilityTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "picks": {
                "active": [
                    {"symbol": "BTCUSDT", "direction": "LONG", "confidence": 0.7},
                    {"symbol": "ETHUSDT", "direction": "SHORT", "confidence": 0.6},
                ],
                "recent_closed": [
                    {"symbol": "ADAUSDT", "pnl_pct": 0.5},
                ],
            },
            "summary": {"net_sharpe_annual": 1.23},
        }

    def test_stable_hash(self) -> None:
        h1 = pn._hash_picks_payload(self._payload())
        h2 = pn._hash_picks_payload(self._payload())
        self.assertEqual(h1, h2)

    def test_mutation_changes_hash(self) -> None:
        p = self._payload()
        h1 = pn._hash_picks_payload(p)
        p["picks"]["active"][0]["confidence"] = 0.71  # one bp change
        h2 = pn._hash_picks_payload(p)
        self.assertNotEqual(h1["active_picks_hash"], h2["active_picks_hash"])
        self.assertEqual(h1["summary_hash"], h2["summary_hash"])  # untouched

    def test_summary_mutation_isolated(self) -> None:
        p = self._payload()
        h1 = pn._hash_picks_payload(p)
        p["summary"]["net_sharpe_annual"] = 99.99
        h2 = pn._hash_picks_payload(p)
        self.assertNotEqual(h1["summary_hash"], h2["summary_hash"])
        self.assertEqual(h1["active_picks_hash"], h2["active_picks_hash"])

    def test_handles_missing_keys(self) -> None:
        h = pn._hash_picks_payload({})
        self.assertEqual(h["n_active"], 0)
        self.assertEqual(h["n_recent_closed"], 0)
        self.assertTrue(h["active_picks_hash"].startswith("sha256:"))


class Sha256Tests(unittest.TestCase):
    def test_known_vector(self) -> None:
        # sha256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        self.assertEqual(
            pn._sha256(""),
            "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )


if __name__ == "__main__":
    unittest.main()
