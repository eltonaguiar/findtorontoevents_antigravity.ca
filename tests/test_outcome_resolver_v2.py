#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for outcome_resolver v2 (asset-class-gated + bar-replay).

These tests pin the v2 fix landing in PR `fix/non-crypto-resolver-bar-replay-2026-04-28`:
  * Per-asset-class WIN threshold (5bp non-crypto, 0.1bp crypto)
  * Bar-replay TP/SL detection that mirrors forward_validator's day_high/day_low
  * No live-spot close when TP/SL was not touched in the OHLC window
  * resolver_version="v2" + _legacy_* preservation

Reference: reports/action_B_resolver_2026_04_27.md
Memory:    feedback_noncrypto_resolver_live_close_bug.md
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import outcome_resolver as orv  # noqa: E402


class TestPerAssetClassThreshold(unittest.TestCase):
    """The v2 threshold map gates each asset class independently."""

    def test_crypto_keeps_tight_threshold(self):
        self.assertEqual(orv._win_threshold_for("CRYPTO"), 0.00001)

    def test_non_crypto_classes_use_5bp_floor(self):
        for cls in ("EQUITY", "ETF", "FOREX", "COMMODITY", "BOND", "FUTURES"):
            self.assertEqual(
                orv._win_threshold_for(cls), 0.0005,
                f"{cls} expected 5bp WIN floor",
            )

    def test_unknown_class_falls_back_to_default(self):
        self.assertEqual(orv._win_threshold_for("UNKNOWN_THING"),
                         orv.PNL_WIN_THRESHOLD_DEFAULT)
        self.assertEqual(orv._win_threshold_for(None),
                         orv.PNL_WIN_THRESHOLD_DEFAULT)
        self.assertEqual(orv._win_threshold_for(""),
                         orv.PNL_WIN_THRESHOLD_DEFAULT)

    def test_loss_threshold_mirrors_win(self):
        self.assertEqual(orv._loss_threshold_for("FOREX"), -0.0005)
        self.assertEqual(orv._loss_threshold_for("CRYPTO"), -0.00001)

    def test_aliases_are_normalized(self):
        # _resolve_asset_class normalizes legacy aliases (STOCKS->EQUITY etc.)
        self.assertEqual(
            orv._resolve_asset_class({"asset_class": "stocks"}), "EQUITY",
        )
        self.assertEqual(
            orv._resolve_asset_class({"asset_class": "FX"}), "FOREX",
        )
        self.assertEqual(
            orv._resolve_asset_class({"asset_class": "Commodities"}), "COMMODITY",
        )

    def test_class_inferred_from_yahoo_suffix(self):
        self.assertEqual(
            orv._resolve_asset_class({"symbol": "EURUSD=X"}), "FOREX",
        )
        self.assertEqual(
            orv._resolve_asset_class({"symbol": "GC=F"}), "COMMODITY",
        )


class TestClassifyOutcomeAssetClassGated(unittest.TestCase):
    """classify_outcome must use the per-class threshold when asset_class is set."""

    def test_non_crypto_3bp_is_flat_not_won(self):
        # 0.0003 = 3bp = below the 5bp non-crypto floor -> FLAT, not WON.
        self.assertEqual(
            orv.classify_outcome(0.0003, asset_class="FOREX"), "FLAT",
        )
        self.assertEqual(
            orv.classify_outcome(0.0003, asset_class="COMMODITY"), "FLAT",
        )

    def test_non_crypto_1pct_is_still_won(self):
        # Regression: real edge (1%) must still classify as WON for non-crypto.
        self.assertEqual(
            orv.classify_outcome(0.01, asset_class="FOREX"), "WON",
        )
        self.assertEqual(
            orv.classify_outcome(-0.01, asset_class="FOREX"), "LOST",
        )

    def test_crypto_3bp_is_still_won(self):
        # Crypto threshold is 0.1bp so 3bp is comfortably above and remains WON.
        self.assertEqual(
            orv.classify_outcome(0.0003, asset_class="CRYPTO"), "WON",
        )

    def test_no_asset_class_keeps_legacy_behavior(self):
        # Backwards compat: callers that don't pass asset_class get the
        # legacy 0.1bp threshold so existing behavior is preserved.
        self.assertEqual(orv.classify_outcome(0.0003), "WON")  # > 0.1bp -> WON
        self.assertEqual(orv.classify_outcome(0.0), "FLAT")


class TestBarReplayScan(unittest.TestCase):
    """_scan_ohlc_for_touch should detect TP/SL hits exactly like forward_validator."""

    def _bar(self, hi: float, lo: float, date: str = "2026-04-25") -> dict:
        return {"date": date, "open": (hi + lo) / 2,
                "high": hi, "low": lo, "close": (hi + lo) / 2}

    def test_long_tp_touched_by_day_high(self):
        # entry 100, TP 105, SL 95 — bar reaches 106 -> TP_HIT_REPLAY
        bars = [self._bar(106, 99)]
        hit = orv._scan_ohlc_for_touch(bars, "LONG", tp=105.0, sl=95.0)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "TP_HIT_REPLAY")
        self.assertEqual(hit["price"], 105.0)

    def test_long_sl_touched_by_day_low(self):
        bars = [self._bar(101, 94)]   # day_low 94 <= SL 95
        hit = orv._scan_ohlc_for_touch(bars, "LONG", tp=110.0, sl=95.0)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "SL_HIT_REPLAY")
        self.assertEqual(hit["price"], 95.0)

    def test_short_tp_touched_by_day_low(self):
        # SHORT entry 100, TP 95, SL 105 — bar reaches 94 -> TP_HIT_REPLAY
        bars = [self._bar(101, 94)]
        hit = orv._scan_ohlc_for_touch(bars, "SHORT", tp=95.0, sl=105.0)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "TP_HIT_REPLAY")
        self.assertEqual(hit["price"], 95.0)

    def test_short_sl_touched_by_day_high(self):
        bars = [self._bar(106, 99)]
        hit = orv._scan_ohlc_for_touch(bars, "SHORT", tp=90.0, sl=105.0)
        self.assertIsNotNone(hit)
        self.assertEqual(hit["reason"], "SL_HIT_REPLAY")
        self.assertEqual(hit["price"], 105.0)

    def test_neither_touched_returns_none(self):
        # Bar stays inside [SL, TP] band.
        bars = [self._bar(102, 98), self._bar(103, 99), self._bar(101, 97)]
        hit = orv._scan_ohlc_for_touch(bars, "LONG", tp=110.0, sl=95.0)
        self.assertIsNone(hit)

    def test_first_bar_wins(self):
        # First bar already touches TP — should return immediately even if a
        # later bar would have hit SL.
        bars = [self._bar(110, 99), self._bar(101, 90)]
        hit = orv._scan_ohlc_for_touch(bars, "LONG", tp=105.0, sl=95.0)
        self.assertEqual(hit["reason"], "TP_HIT_REPLAY")
        self.assertEqual(hit["bar_date"], bars[0]["date"])

    def test_sl_priority_when_both_touched_same_bar(self):
        # Conservative tie-break: same bar touches both TP and SL -> SL.
        bars = [self._bar(110, 90)]
        hit = orv._scan_ohlc_for_touch(bars, "LONG", tp=105.0, sl=95.0)
        self.assertEqual(hit["reason"], "SL_HIT_REPLAY")

    def test_empty_bars_returns_none(self):
        self.assertIsNone(orv._scan_ohlc_for_touch([], "LONG", 105.0, 95.0))

    def test_no_tp_no_sl_returns_none(self):
        bars = [self._bar(110, 90)]
        self.assertIsNone(orv._scan_ohlc_for_touch(bars, "LONG", 0.0, 0.0))


class TestResolveSinglePickV2(unittest.TestCase):
    """resolve_single_pick must close at TP from bar replay, NOT at live spot."""

    def test_long_pick_with_tp_touched_in_window_resolves_at_tp(self):
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.10000,
            "take_profit": 1.10500,   # 50bp above entry
            "stop_loss":   1.09500,   # 50bp below entry
        }
        # Day_high reaches 1.106 -> touches TP at 1.105.
        bars = [{"date": "2026-04-25", "open": 1.1005, "high": 1.106,
                 "low": 1.099, "close": 1.103}]
        live_spot = 1.10010   # nearly entry — would have given +1bp under legacy

        out = orv.resolve_single_pick(pick.copy(), live_price=live_spot,
                                       ohlc_window=bars)
        self.assertEqual(out["exit_reason"], "TP_HIT_REPLAY")
        self.assertAlmostEqual(out["exit_price"], 1.10500, places=5)
        # PnL from entry 1.10 -> 1.105 = ~0.4545% = comfortably above 5bp.
        self.assertGreater(out["pnl_pct"], 0.0040)
        self.assertEqual(out["status"], "WON")
        self.assertTrue(out["resolver_version"].startswith("v2"), f"resolver_version should start with v2, got {out['resolver_version']}")

    def test_long_pick_no_touch_returns_still_active(self):
        # Critical regression: legacy bug closed at live spot -> noise win.
        # v2 must leave the pick alone (no exit_price written).
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.10000,
            "take_profit": 1.10500,
            "stop_loss":   1.09500,
        }
        # Bar stays inside [SL, TP] band.
        bars = [{"date": "2026-04-25", "open": 1.1003, "high": 1.1010,
                 "low": 1.0997, "close": 1.1005}]
        # Live spot drifted up — under the legacy bug this would have closed
        # the pick at 1.10030 with exit_reason=PRICE_RESOLVED and pnl=+2.7bp.
        live_spot = 1.10030

        out = orv.resolve_single_pick(pick.copy(), live_price=live_spot,
                                       ohlc_window=bars)
        # Pick must NOT have been closed — no exit_price overwrite, retry flag set.
        self.assertTrue(out.get("_resolve_retry_needed"))
        self.assertTrue(out.get("_resolver_v2_no_touch"))
        # The legacy "PRICE_RESOLVED" exit_reason must NOT have been written.
        self.assertNotIn("PRICE_RESOLVED", str(out.get("exit_reason", "")))

    def test_short_pick_with_sl_touched_resolves_at_sl(self):
        pick = {
            "symbol": "GC=F",
            "asset_class": "COMMODITY",
            "direction": "SHORT",
            "entry_price": 2400.0,
            "take_profit": 2300.0,   # 100 below (SHORT TP)
            "stop_loss":   2440.0,   # 40 above (SHORT SL)
        }
        # Day_high reached 2450 -> touches SL at 2440.
        bars = [{"date": "2026-04-25", "open": 2410.0, "high": 2450.0,
                 "low": 2395.0, "close": 2415.0}]

        out = orv.resolve_single_pick(pick.copy(), live_price=2400.0,
                                       ohlc_window=bars)
        self.assertEqual(out["exit_reason"], "SL_HIT_REPLAY")
        self.assertAlmostEqual(out["exit_price"], 2440.0, places=2)
        # SHORT entry 2400 -> exit 2440 = -1.67% PnL
        self.assertLess(out["pnl_pct"], -0.005)
        self.assertEqual(out["status"], "LOST")
        self.assertTrue(out["resolver_version"].startswith("v2"), f"resolver_version should start with v2, got {out['resolver_version']}")

    def test_legacy_fields_preserved_on_v2_resolution(self):
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.10000,
            "take_profit": 1.10500,
            "stop_loss":   1.09500,
            # Pre-existing legacy fields that v2 should preserve as _legacy_*
            "pnl_pct": 0.0001,            # legacy 1bp WIN — noise under v2
            "exit_reason": "FORCE_CLOSED",
        }
        bars = [{"date": "2026-04-25", "open": 1.1010, "high": 1.106,
                 "low": 1.099, "close": 1.103}]

        out = orv.resolve_single_pick(pick.copy(), live_price=1.10100,
                                       ohlc_window=bars)
        self.assertEqual(out["_legacy_pnl_pct"], 0.0001)
        self.assertEqual(out["_legacy_exit_reason"], "FORCE_CLOSED")
        self.assertTrue(out["resolver_version"].startswith("v2"), f"resolver_version should start with v2, got {out['resolver_version']}")
        # New labels overwrite, not the legacy ones.
        self.assertEqual(out["exit_reason"], "TP_HIT_REPLAY")

    def test_crypto_unaffected_by_v2_path(self):
        # CRYPTO uses the legacy live-spot path (no bar-replay). C1 Path B/C fix:
        # exit_price is now the observed live_price (51500), NOT the nominal TP
        # (51000). Crediting the nominal TP pinned every win to exactly the TP
        # distance — the ghost-row artifact. live_price is the genuine fill witness.
        pick = {
            "symbol": "BTCUSDT",
            "asset_class": "CRYPTO",
            "direction": "LONG",
            "entry_price": 50000.0,
            "take_profit": 51000.0,
            "stop_loss":   49000.0,
        }
        out = orv.resolve_single_pick(pick.copy(), live_price=51500.0,
                                       ohlc_window=None)
        self.assertEqual(out["status"], "WON")
        self.assertEqual(out["exit_reason"], "TP_HIT_RESOLVED")
        self.assertAlmostEqual(out["exit_price"], 51500.0, places=2)  # C1 Path B/C: real fill price

    def test_non_crypto_with_no_ohlc_does_not_close_at_live_spot(self):
        # Critical regression. The legacy bug was: non-crypto pick + live_spot
        # -> close at PRICE_RESOLVED. v2 must refuse and flag retry.
        pick = {
            "symbol": "EURUSD=X",
            "asset_class": "FOREX",
            "direction": "LONG",
            "entry_price": 1.10000,
            "take_profit": 1.10500,
            "stop_loss":   1.09500,
        }
        out = orv.resolve_single_pick(pick.copy(), live_price=1.10030,
                                       ohlc_window=None)
        self.assertTrue(out.get("_resolve_retry_needed"))
        self.assertTrue(out.get("_resolver_v2_no_ohlc"))
        # status must NOT be WON/LOST/FLAT — pick is unchanged.
        self.assertNotIn(out.get("status", ""), ("WON", "LOST", "FLAT"))


class TestNoiseFilterRegression(unittest.TestCase):
    """Pin the audit's noise criterion: |pnl| < 5bp on non-crypto -> FLAT, not WON."""

    def test_3bp_forex_win_now_flat(self):
        # Reproduces the audit's 'FOREX 253/400 noise wins' pattern: a tiny
        # positive pnl that under v1 was labeled WON.
        self.assertEqual(orv.classify_outcome(0.0003, asset_class="FOREX"), "FLAT")

    def test_3bp_commodity_loss_now_flat(self):
        self.assertEqual(orv.classify_outcome(-0.0003, asset_class="COMMODITY"), "FLAT")

    def test_6bp_forex_win_still_counts(self):
        # Just above the floor — should remain WON.
        self.assertEqual(orv.classify_outcome(0.0006, asset_class="FOREX"), "WON")

    def test_50bp_loss_classifies_as_lost(self):
        self.assertEqual(orv.classify_outcome(-0.005, asset_class="FOREX"), "LOST")


if __name__ == "__main__":
    unittest.main(verbosity=2)
