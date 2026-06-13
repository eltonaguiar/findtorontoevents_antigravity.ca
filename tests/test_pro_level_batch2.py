"""Batch2 tests: luxalgo fallback + commodity gap-fade replay stats."""
import os
import sys
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tools.replay_commodity_gap_fade_intrabar import _stats  # noqa: E402


class TestGapFadeReplay(unittest.TestCase):
    def test_stats_empty(self):
        s = _stats([])
        self.assertEqual(s["n"], 0)
        self.assertEqual(s["wr_pct"], 0.0)

    def test_stats_mixed(self):
        rows = [
            {"intrabar_status": "TP_HIT", "intrabar_pnl_pct": 2.0},
            {"intrabar_status": "SL_HIT", "intrabar_pnl_pct": -1.0},
            {"intrabar_status": "TP_HIT", "intrabar_pnl_pct": 1.5},
        ]
        s = _stats(rows)
        self.assertEqual(s["n"], 3)
        self.assertEqual(s["wins"], 2)
        self.assertAlmostEqual(s["wr_pct"], 66.7, places=1)
        self.assertAlmostEqual(s["pf"], 3.5, places=1)


class TestLuxalgoFallback(unittest.TestCase):
    def test_fallback_emits_short_when_scanner_empty(self):
        from alpha_engine.june2026_research_candidates import _generate_luxalgo_short_v2

        with patch("alpha_engine.scanner.run_luxalgo_confluence_scan", return_value=[], create=True):
            picks = _generate_luxalgo_short_v2()
        self.assertGreaterEqual(len(picks), 1)
        self.assertTrue(all(str(p.get("direction", "")).upper() in ("SHORT", "SELL") for p in picks))
        self.assertEqual(picks[0].get("symbol"), "NEARUSDT")


if __name__ == "__main__":
    unittest.main()
