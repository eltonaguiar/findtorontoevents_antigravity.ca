"""Unit tests for tools/regime_strategy_matcher.py."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.regime_strategy_matcher import (  # noqa: E402
    classify_strategy_style,
    match_verdict,
    backtest_on_closed,
    RegimeDetector,
)


class StrategyStyleClassifierTests(unittest.TestCase):
    def test_mean_rev_markers(self):
        for name in (
            "rsi2_mean_reversion",
            "forex_rsi2_mean_reversion",
            "bollinger_mr",
            "fear_greed_contrarian",
            "st_fear_greed_contrarian",
            "vwap_deviation_reversion",
            "st_obv_support_divergence",
            "luxalgo_confluence",
        ):
            self.assertEqual(classify_strategy_style(name), "MEAN_REVERTING", name)

    def test_trend_markers(self):
        for name in (
            "futures_momentum",
            "breakout_momentum",
            "macd_crossover",
            "cta_cross_asset_tsmom",
            "donchian_breakout",
            "ema_stack_momentum",
            "multi_period_rsi_confluence_eth",
        ):
            self.assertEqual(classify_strategy_style(name), "TREND", name)

    def test_unknown(self):
        self.assertEqual(classify_strategy_style("random_strategy_xyz"), "UNKNOWN")
        self.assertEqual(classify_strategy_style(""), "UNKNOWN")
        self.assertEqual(classify_strategy_style(None), "UNKNOWN")


class MatchVerdictTests(unittest.TestCase):
    def test_mean_rev_in_trending_down_rejected(self):
        pick = dict(strategy="fear_greed_contrarian", pnl_pct=0.5)
        regime = {"regime": "TRENDING_DOWN", "confidence": 0.8}
        v = match_verdict(pick, regime_info=regime)
        self.assertFalse(v["allow"])
        self.assertIn("mean_rev_in_trending_down", v["reason"])

    def test_trend_in_mean_reverting_rejected(self):
        pick = dict(strategy="futures_momentum", pnl_pct=0.5)
        regime = {"regime": "MEAN_REVERTING", "confidence": 0.75}
        v = match_verdict(pick, regime_info=regime)
        self.assertFalse(v["allow"])
        self.assertIn("trend_in_mean_reverting", v["reason"])

    def test_mean_rev_in_mean_reverting_allowed(self):
        """The key test: yesterday's bounce day. fear-greed-contrarian should fire."""
        pick = dict(strategy="st_fear_greed_contrarian", pnl_pct=0.5)
        regime = {"regime": "MEAN_REVERTING", "confidence": 0.75}
        v = match_verdict(pick, regime_info=regime)
        self.assertTrue(v["allow"])
        self.assertIn("MEAN_REVERTING_ok_in_MEAN_REVERTING", v["reason"])

    def test_trend_in_trending_up_allowed(self):
        pick = dict(strategy="breakout_momentum", pnl_pct=0.5)
        regime = {"regime": "TRENDING_UP", "confidence": 0.7}
        v = match_verdict(pick, regime_info=regime)
        self.assertTrue(v["allow"])

    def test_unknown_regime_fails_open(self):
        pick = dict(strategy="fear_greed_contrarian", pnl_pct=0.5)
        regime = {"regime": "UNKNOWN", "confidence": 0.0}
        v = match_verdict(pick, regime_info=regime)
        self.assertTrue(v["allow"])
        self.assertEqual(v["reason"], "regime_unknown_fail_open")

    def test_unknown_style_fails_open(self):
        pick = dict(strategy="weird_novel_strategy", pnl_pct=0.5)
        regime = {"regime": "TRENDING_DOWN", "confidence": 0.8}
        v = match_verdict(pick, regime_info=regime)
        self.assertTrue(v["allow"])
        self.assertEqual(v["reason"], "strategy_style_unknown_fail_open")

    def test_high_volatility_allows_all(self):
        """HIGH_VOLATILITY is treated as neutral — both styles allowed."""
        for strat in ("fear_greed_contrarian", "futures_momentum"):
            pick = dict(strategy=strat, pnl_pct=0.5)
            regime = {"regime": "HIGH_VOLATILITY", "confidence": 0.8}
            v = match_verdict(pick, regime_info=regime)
            self.assertTrue(v["allow"], strat)


class BacktestTests(unittest.TestCase):
    def test_backtest_shape(self):
        picks = [
            dict(strategy="fear_greed_contrarian", pnl_pct=5.0),
            dict(strategy="futures_momentum", pnl_pct=-1.0),
            dict(strategy="random_xyz", pnl_pct=0.5),
        ]
        out = backtest_on_closed(picks, regime_info={"regime": "MEAN_REVERTING", "confidence": 0.75})
        self.assertIn("baseline", out)
        self.assertIn("allowed", out)
        self.assertIn("rejected", out)
        self.assertEqual(out["baseline"]["n"], 3)

    def test_yesterday_bounce_behavior(self):
        """Simulates 2026-04-20 regime: MEAN_REVERTING.
        fear-greed-contrarian wins should be kept; momentum losses rejected."""
        picks = [
            dict(strategy="st_fear_greed_contrarian", pnl_pct=2.0),  # winner, MEAN_REV -> ALLOWED
            dict(strategy="st_fear_greed_contrarian", pnl_pct=1.5),  # winner, MEAN_REV -> ALLOWED
            dict(strategy="cta_cross_asset_tsmom", pnl_pct=-2.0),    # loser, TREND -> REJECTED
            dict(strategy="breakout_momentum", pnl_pct=-0.5),        # loser, TREND -> REJECTED
        ]
        out = backtest_on_closed(
            picks, regime_info={"regime": "MEAN_REVERTING", "confidence": 0.75}
        )
        # Allowed: the 2 fear-greed-contrarian winners
        self.assertEqual(out["allowed"]["n"], 2)
        self.assertAlmostEqual(out["allowed"]["cum_pct"], 3.5)
        # Rejected: 2 trend picks (both losers — good!)
        self.assertEqual(out["rejected"]["n"], 2)
        self.assertLess(out["rejected"]["cum_pct"], 0)


class RegimeDetectorShapeTests(unittest.TestCase):
    def test_classify_unknown_when_too_few_prices(self):
        d = RegimeDetector()
        result = d._classify([100.0, 101.0], fg=50)
        self.assertEqual(result["regime"], "UNKNOWN")

    def test_classify_high_vol(self):
        # Synthetic extreme volatility series
        import random
        rng = random.Random(1)
        closes = [100.0]
        for _ in range(60):
            closes.append(closes[-1] * (1 + rng.gauss(0, 0.1)))  # 10% daily moves
        d = RegimeDetector()
        r = d._classify(closes, fg=50)
        self.assertIn(r["regime"], ("HIGH_VOLATILITY", "MEAN_REVERTING", "UNKNOWN"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
