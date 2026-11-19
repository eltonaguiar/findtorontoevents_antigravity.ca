#!/usr/bin/env python3
"""Unit tests for the discovery rights-gate (publish path).

Run: python3 ideas/bestiejob/prototypes/test_rights_gate.py
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "updates" / "scripts"))

from discover_sn_sf_dev import is_publishable, load_rights  # noqa: E402


class RightsGateTest(unittest.TestCase):
    def test_explicit_false_blocks_even_if_approved(self):
        self.assertFalse(is_publishable({"rights": "redistribution_approved", "redistribute": False}))

    def test_explicit_true_allows(self):
        self.assertTrue(is_publishable({"rights": "manual_discovery", "redistribute": True}))

    def test_approved_without_flag_allows(self):
        self.assertTrue(is_publishable({"rights": "redistribution_approved"}))

    def test_own_site_attributed_allows(self):
        self.assertTrue(is_publishable({"rights": "own_site_attributed"}))

    def test_private_blocks(self):
        self.assertFalse(is_publishable({"rights": "permitted_api_private", "redistribute": False}))

    def test_manual_discovery_blocks(self):
        self.assertFalse(is_publishable({"rights": "manual_discovery", "redistribute": False}))

    def test_unknown_blocks(self):
        self.assertFalse(is_publishable({}))
        self.assertFalse(is_publishable({"rights": "unknown"}))

    def test_loaded_config_has_core_sources(self):
        r = load_rights()
        for src in ("readme", "linkedin", "workday"):
            self.assertIn(src, r)
        # LinkedIn/Workday must never be publicly redistributed
        self.assertFalse(is_publishable(r["linkedin"]))
        self.assertFalse(is_publishable(r["workday"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
