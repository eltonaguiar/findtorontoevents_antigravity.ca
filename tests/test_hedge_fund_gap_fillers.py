"""Unit tests for the hedge-fund gap-filler tools:
    tools/triple_barrier_labeler.py
    tools/risk_parity_allocator.py
    tools/meta_labeler.py
    tools/risk_metrics.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.triple_barrier_labeler import label_pick, label_closed_picks, audit_labels  # noqa: E402
from tools.risk_parity_allocator import (  # noqa: E402
    per_class_returns,
    compute_risk_parity_weights,
    summarize_allocation,
)
from tools.meta_labeler import (  # noqa: E402
    extract_features,
    pnl_to_label,
    MetaLabelModel,
    train_meta_labeler_from_closed,
)
from tools.risk_metrics import (  # noqa: E402
    sortino,
    probabilistic_sharpe_ratio,
    max_drawdown,
    calmar,
    ulcer_index,
    compute_all,
)


# ====================== TRIPLE-BARRIER LABELER ======================

class TripleBarrierLabelerTests(unittest.TestCase):
    def test_win_from_positive_pnl(self):
        p = dict(id="t1", symbol="BTCUSDT", direction="LONG",
                 entry_price=100, take_profit=110, stop_loss=95, pnl_pct=5.0)
        r = label_pick(p)
        self.assertEqual(r["label"], "WIN")
        self.assertEqual(r["first_barrier"], "TP")

    def test_loss_from_negative_pnl(self):
        p = dict(id="t2", direction="LONG",
                 entry_price=100, take_profit=110, stop_loss=95, pnl_pct=-3.0)
        r = label_pick(p)
        self.assertEqual(r["label"], "LOSS")
        self.assertEqual(r["first_barrier"], "SL")

    def test_flat_close_bug_detected(self):
        # Zero pnl + degenerate barriers (entry=tp=sl=0)
        p = dict(id="t3", direction="LONG",
                 entry_price=0, take_profit=0, stop_loss=0, pnl_pct=0.0)
        r = label_pick(p)
        self.assertEqual(r["label"], "FLAT_CLOSE_BUG")
        self.assertEqual(r["first_barrier"], "NONE")

    def test_audit_flags_broken_strategies(self):
        picks = [dict(id=f"t{i}", strategy="broken_strat", direction="LONG",
                      entry_price=0, take_profit=0, stop_loss=0, pnl_pct=0.0)
                 for i in range(15)]
        labels = label_closed_picks(picks)
        report = audit_labels(labels, picks)
        self.assertEqual(len(report["broken_strategies"]), 1)
        self.assertEqual(report["broken_strategies"][0]["strategy"], "broken_strat")
        self.assertGreaterEqual(report["broken_strategies"][0]["flat_close_rate_pct"], 50)

    def test_audit_ignores_small_samples(self):
        # Only 5 flat closes — below the n>=10 threshold
        picks = [dict(id=f"t{i}", strategy="small", direction="LONG",
                      entry_price=0, take_profit=0, stop_loss=0, pnl_pct=0.0)
                 for i in range(5)]
        report = audit_labels(label_closed_picks(picks), picks)
        self.assertEqual(len(report["broken_strategies"]), 0)


# ====================== RISK PARITY ALLOCATOR ======================

class RiskParityAllocatorTests(unittest.TestCase):
    def _picks(self):
        # Synthesize: CRYPTO high vol, EQUITY low vol, FOREX medium vol
        crypto = [dict(asset_class="CRYPTO", pnl_pct=(-5 + 0.3 * i)) for i in range(25)]
        equity = [dict(asset_class="EQUITY", pnl_pct=(0.5 + 0.02 * i)) for i in range(25)]
        forex = [dict(asset_class="FOREX", pnl_pct=(-0.5 + 0.08 * i)) for i in range(25)]
        return crypto + equity + forex

    def test_per_class_returns_splits(self):
        bs = per_class_returns(self._picks())
        self.assertEqual(len(bs["CRYPTO"]), 25)
        self.assertEqual(len(bs["EQUITY"]), 25)
        self.assertEqual(len(bs["FOREX"]), 25)

    def test_inverse_vol_lowest_weight_on_highest_vol(self):
        weights = compute_risk_parity_weights(self._picks(), min_n=20)
        # Crypto had stdev 2.16 (synthetic), forex 1.16, equity 0.14
        # Inverse-vol weights should put EQUITY highest, CRYPTO lowest
        self.assertGreater(weights["EQUITY"]["target_weight_pct"],
                           weights["CRYPTO"]["target_weight_pct"])

    def test_below_min_n_excluded(self):
        picks = [dict(asset_class="CRYPTO", pnl_pct=1.0)] * 5
        weights = compute_risk_parity_weights(picks, min_n=20)
        self.assertIn("CRYPTO", weights)
        self.assertEqual(weights["CRYPTO"].get("target_weight_pct", 0), 0)

    def test_summarize_shape(self):
        weights = compute_risk_parity_weights(self._picks(), min_n=20)
        summary = summarize_allocation(weights)
        self.assertIn("eligible_classes", summary)
        self.assertIn("allocations", summary)
        self.assertGreater(len(summary["allocations"]), 0)


# ====================== META-LABELER ======================

class MetaLabelerTests(unittest.TestCase):
    def test_extract_features_shape(self):
        picks = [dict(symbol="BTCUSDT", asset_class="CRYPTO", direction="LONG",
                      score=70, elite_score=65, ml_composite_score=55,
                      confidence=0.8, risk_reward=2.5, rsi_at_entry=50,
                      entry_time="2026-04-21T14:00:00Z")]
        features = extract_features(picks)
        self.assertEqual(len(features), 1)
        self.assertIn("score", features[0])
        self.assertIn("is_crypto", features[0])
        self.assertEqual(features[0]["is_crypto"], 1.0)
        self.assertEqual(features[0]["is_equity"], 0.0)
        self.assertEqual(features[0]["hour_utc"], 14.0)

    def test_kill_window_flag(self):
        p = [dict(symbol="X", asset_class="CRYPTO", direction="LONG",
                  entry_time="2026-04-21T09:00:00Z")]
        f = extract_features(p)[0]
        self.assertEqual(f["is_kill_window"], 1.0)
        p2 = [dict(symbol="X", asset_class="CRYPTO", direction="LONG",
                   entry_time="2026-04-21T14:00:00Z")]
        f2 = extract_features(p2)[0]
        self.assertEqual(f2["is_kill_window"], 0.0)

    def test_pnl_to_label(self):
        self.assertEqual(pnl_to_label(2.0), 1)
        self.assertEqual(pnl_to_label(-1.0), 0)
        self.assertEqual(pnl_to_label(0.005), 0)  # below threshold
        self.assertIsNone(pnl_to_label(None))

    def test_model_scaffold_predicts_prior(self):
        m = MetaLabelModel(default_prob_win=0.6)
        features = [{"a": 1}, {"a": 2}]
        probs = m.predict_proba(features)
        self.assertEqual(len(probs), 2)
        for p in probs:
            self.assertAlmostEqual(p[1], 0.6)

    def test_train_from_closed(self):
        closed = [
            dict(symbol="X", asset_class="CRYPTO", direction="LONG", pnl_pct=2.0,
                 entry_time="2026-04-21T14:00:00Z"),
            dict(symbol="X", asset_class="CRYPTO", direction="LONG", pnl_pct=-1.0,
                 entry_time="2026-04-21T15:00:00Z"),
            dict(symbol="X", asset_class="CRYPTO", direction="LONG", pnl_pct=None,
                 entry_time="2026-04-21T16:00:00Z"),  # excluded
        ]
        model, n_train, n_pos = train_meta_labeler_from_closed(closed)
        self.assertEqual(n_train, 2)
        self.assertEqual(n_pos, 1)
        self.assertTrue(model.fitted)


# ====================== RISK METRICS ======================

class RiskMetricsTests(unittest.TestCase):
    def test_sortino_zero_downside(self):
        # All positive returns => no downside => Sortino returns 0 (by convention)
        self.assertEqual(sortino([1.0, 2.0, 3.0]), 0.0)

    def test_sortino_with_downside(self):
        s = sortino([1.0, -0.5, 2.0, -1.0, 1.5])
        self.assertGreater(s, 0)

    def test_psr_positive_drift(self):
        import random
        rng = random.Random(7)
        returns = [round(rng.gauss(1.0, 0.5), 4) for _ in range(100)]
        p = probabilistic_sharpe_ratio(returns, 0.0)
        self.assertGreater(p, 0.95)

    def test_psr_zero_drift(self):
        returns = [1.0 if i % 2 == 0 else -1.0 for i in range(50)]
        p = probabilistic_sharpe_ratio(returns, 0.0)
        self.assertLess(p, 0.7)

    def test_max_drawdown_monotonic_positive(self):
        dd = max_drawdown([1.0, 1.0, 1.0, 1.0])
        self.assertEqual(dd["max_drawdown_pct"], 0.0)

    def test_max_drawdown_simple(self):
        # +1, -5, +2 => cum: [1, -4, -2]; peak 1 at idx 0, trough -4 at idx 1, dd = -5
        dd = max_drawdown([1.0, -5.0, 2.0])
        self.assertAlmostEqual(dd["max_drawdown_pct"], -5.0)
        self.assertEqual(dd["peak_idx"], 0)
        self.assertEqual(dd["trough_idx"], 1)

    def test_calmar(self):
        # cum = +10, max_dd = -5 => Calmar 2.0
        returns = [5.0, -5.0, 10.0]  # cum: 5, 0, 10; peak 5->0 dd=-5
        c = calmar(returns)
        self.assertAlmostEqual(c, 2.0)

    def test_ulcer_index_nonneg(self):
        ui = ulcer_index([1.0, -0.5, 2.0, -3.0, 1.0])
        self.assertGreaterEqual(ui, 0.0)

    def test_compute_all_shape(self):
        returns = [1.0, -0.5, 2.0, -1.0, 1.5, 0.8, -0.3, 1.2, 0.6, -0.2]
        res = compute_all(returns)
        for k in ("n", "mean_return_pct", "stdev_pct", "sharpe_per_trade",
                  "sortino", "psr_vs_sr0", "calmar", "max_drawdown_pct",
                  "ulcer_index_pct", "cum_return_pct"):
            self.assertIn(k, res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
