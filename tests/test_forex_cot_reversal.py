"""Tests for forex_cot_reversal + cftc_cot_forex_fetcher.

Covers:
  1. Fetcher graceful-failure when gate OFF (default).
  2. 52w percentile computation correctness.
  3. SHORT signal at >=80th percentile with 2-week confirm.
  4. LONG signal at <=20th percentile with 2-week confirm.
  5. 2-week confirmation requirement (single-week extreme -> NEUTRAL).
  6. Default-OFF: forex_cot_reversal_picks() == [] without env var.
  7. Pick shape: confidence=0, status=paper_only, forex_size_capped=True.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from alpha_engine import forex_cot_reversal as fcr  # noqa: E402
from tools import cftc_cot_forex_fetcher as fetcher  # noqa: E402


def _mk_reports(nc_nets: list[float], cm_nets: list[float] | None = None,
                start_date: str = "2026-05-06") -> list[dict]:
    """Build CFTC-Socrata-shaped reports list, newest first.

    `nc_nets[0]` is the most recent week. Decreases by 7d per row.
    """
    from datetime import datetime, timedelta
    d0 = datetime.strptime(start_date, "%Y-%m-%d")
    cm_nets = cm_nets if cm_nets is not None else [0.0] * len(nc_nets)
    rows = []
    for i, (nc, cm) in enumerate(zip(nc_nets, cm_nets)):
        # Split arbitrarily into long/short halves around the net.
        nc_long = max(50_000 + int(nc) // 2, 0)
        nc_short = max(50_000 - int(nc) // 2, 0)
        cm_long = max(50_000 + int(cm) // 2, 0)
        cm_short = max(50_000 - int(cm) // 2, 0)
        d = d0 - timedelta(days=7 * i)
        rows.append({
            "report_date_as_yyyy_mm_dd": d.strftime("%Y-%m-%d"),
            "noncomm_positions_long_all": nc_long,
            "noncomm_positions_short_all": nc_short,
            "comm_positions_long_all": cm_long,
            "comm_positions_short_all": cm_short,
        })
    return rows


def _frozen_now():
    from datetime import datetime, timezone
    return datetime(2026, 5, 7, tzinfo=timezone.utc)


class TestFetcherGracefulFailure(unittest.TestCase):
    def test_gate_off_returns_empty(self):
        env = {k: v for k, v in os.environ.items()
               if k != "FOREX_COT_REVERSAL_ENABLED"}
        with patch.dict(os.environ, env, clear=True):
            result = fetcher.fetch_cot("EURUSD")
        self.assertEqual(result["reports"], [])
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertIn("contract", result)

    def test_unknown_symbol_empty(self):
        with patch.dict(os.environ, {"FOREX_COT_REVERSAL_ENABLED": "1"}):
            result = fetcher.fetch_cot("XXXYYY")
        self.assertEqual(result["reports"], [])


class TestPercentile(unittest.TestCase):
    def test_percentile_rank_basic(self):
        import numpy as np
        window = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        self.assertEqual(fcr._percentile_rank(window, 50.0), 100.0)
        self.assertEqual(fcr._percentile_rank(window, 10.0), 20.0)
        self.assertEqual(fcr._percentile_rank(window, 30.0), 60.0)

    def test_percentile_in_compute_signal(self):
        # Build 60 rows: 59 rows uniformly distributed -1000..+1000,
        # newest = +1500 (above all -> 100th pct), prior = +1400 (also top).
        nets = [1500.0, 1400.0] + [float(x) for x in range(-1000, 1000, 35)][:58]
        reports = _mk_reports(nets)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertEqual(sig["direction"], "SHORT")
        self.assertGreaterEqual(sig["percentile_rank"], 95.0)


class TestSignalDirection(unittest.TestCase):
    def test_short_at_extreme_long(self):
        # Newest 2 rows are top-tier (>= 80th pct in 52w window).
        baseline = [float(x) for x in range(-500, 500, 20)][:58]  # 50 mids
        nets = [1500.0, 1450.0] + baseline
        reports = _mk_reports(nets)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertEqual(sig["signal"], "SELL")
        self.assertEqual(sig["direction"], "SHORT")
        self.assertGreaterEqual(sig["raw_confidence"], fcr.RAW_CONFIDENCE_MIN)
        self.assertLessEqual(sig["raw_confidence"], fcr.RAW_CONFIDENCE_MAX)

    def test_long_at_extreme_short(self):
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [-1500.0, -1450.0] + baseline
        reports = _mk_reports(nets)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertEqual(sig["signal"], "BUY")
        self.assertEqual(sig["direction"], "LONG")

    def test_two_week_confirmation_required(self):
        # Only the newest week is extreme; prior is mid.
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [1500.0, 0.0] + baseline
        reports = _mk_reports(nets)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertEqual(sig["direction"], "NEUTRAL")

    def test_commercial_confirmation_boost(self):
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [1500.0, 1450.0] + baseline
        # Commercials net SHORT (negative) -> confirms speculator-long fade.
        cm = [-2000.0, -1900.0] + [0.0] * 58
        reports = _mk_reports(nets, cm_nets=cm)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertTrue(sig["commercial_confirms"])

    def test_insufficient_history(self):
        nets = [1500.0] * 10  # <52w
        reports = _mk_reports(nets)
        sig = fcr.compute_signal(reports, now=_frozen_now())
        self.assertEqual(sig["direction"], "NEUTRAL")

    def test_stale_report(self):
        from datetime import datetime, timezone
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [1500.0, 1450.0] + baseline
        reports = _mk_reports(nets, start_date="2025-01-01")
        sig = fcr.compute_signal(reports,
                                  now=datetime(2026, 5, 7, tzinfo=timezone.utc))
        self.assertTrue(sig["stale"])
        self.assertEqual(sig["direction"], "NEUTRAL")


class TestDefaultOff(unittest.TestCase):
    def test_default_off_no_picks(self):
        env = {k: v for k, v in os.environ.items()
               if k != "FOREX_COT_REVERSAL_ENABLED"}
        with patch.dict(os.environ, env, clear=True):
            picks = fcr.forex_cot_reversal_picks()
        self.assertEqual(picks, [])


class TestPickShape(unittest.TestCase):
    def test_pick_fields_when_enabled(self):
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [1500.0, 1450.0] + baseline
        reports = _mk_reports(nets)
        fake = {"contract": "099741", "symbol": "EURUSD", "reports": reports}

        with patch.dict(os.environ, {"FOREX_COT_REVERSAL_ENABLED": "1"}):
            with patch.object(fcr, "fetch_cot", return_value=fake):
                picks = fcr.forex_cot_reversal_picks(now=_frozen_now())

        self.assertGreater(len(picks), 0)
        p = picks[0]
        # FOREX hard-cap invariants:
        self.assertEqual(p["confidence"], 0.0)
        self.assertEqual(p["status"], "paper_only")
        self.assertTrue(p["forex_size_capped"])
        self.assertGreaterEqual(p["raw_confidence"], fcr.RAW_CONFIDENCE_MIN)
        # Strategy + asset class:
        self.assertEqual(p["strategy"], "forex_cot_positioning_reversal")
        self.assertEqual(p["asset_class"], "FOREX")
        # Direction one of LONG/SHORT (USDJPY inverts):
        self.assertIn(p["direction"], ("LONG", "SHORT"))

    def test_usdjpy_inversion(self):
        # YEN futures spec long -> compute_signal SHORT -> USDJPY pick LONG.
        baseline = [float(x) for x in range(-500, 500, 20)][:58]
        nets = [1500.0, 1450.0] + baseline
        reports = _mk_reports(nets)
        fake = {"contract": "097741", "symbol": "USDJPY", "reports": reports}

        with patch.dict(os.environ, {"FOREX_COT_REVERSAL_ENABLED": "1"}):
            with patch.object(fcr, "fetch_cot",
                              side_effect=lambda sym: fake if sym == "USDJPY"
                              else {"contract": "", "symbol": sym, "reports": []}):
                picks = fcr.forex_cot_reversal_picks(now=_frozen_now())

        usdjpy = [p for p in picks if p["symbol"] == "USDJPY"]
        self.assertEqual(len(usdjpy), 1)
        # YEN spec long (would be SHORT) inverts to USDJPY LONG.
        self.assertEqual(usdjpy[0]["direction"], "LONG")
        self.assertEqual(usdjpy[0]["signal"], "BUY")


if __name__ == "__main__":
    unittest.main()
