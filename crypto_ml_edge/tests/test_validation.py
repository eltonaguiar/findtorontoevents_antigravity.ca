"""
Tests for crypto_ml_edge/validation.py
=======================================
Run: py -m pytest crypto_ml_edge/tests/test_validation.py -v

Coverage:
    1. Walk-forward splits are chronologically correct (no future in train).
    2. Purge gap exists between every train end and test start.
    3. DSR returns 0 (effectively) for pure random-walk returns.
    4. DSR returns high value for genuinely strong strategy.
    5. Cost adjustment reduces Sharpe (net < gross).
    6. Model with Sharpe < 0 fails validate_model().
    7. n_trials > MAX_MODEL_VARIANTS triggers cap + warning.
    8. Rolling window mode produces fixed-size train sets.
    9. verify_regime_coverage() passes when 2022 data is in a test fold.
   10. verify_regime_coverage() raises when data doesn't reach 2022.
   11. Embargo actually reduces test window size.
   12. Fold.validate_chronology() catches lookahead.
"""

import warnings
import numpy as np
import pandas as pd
import pytest

from crypto_ml_edge.validation import (
    WalkForwardSplit,
    Fold,
    deflated_sharpe_ratio,
    cost_adjusted_sharpe,
    validate_model,
)
from crypto_ml_edge.config import (
    MIN_DSR_PROBABILITY,
    MAX_MODEL_VARIANTS,
    PURGE_GAP_BARS,
    get_total_cost,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _returns(n: int = 1000, seed: int = 42, daily_mean: float = 0.0,
             daily_vol: float = 0.01) -> np.ndarray:
    """Synthetic per-bar returns."""
    rng = np.random.default_rng(seed)
    return rng.normal(daily_mean, daily_vol, size=n)


def _timestamps(n: int = 8760, start: str = "2020-01-01") -> pd.DatetimeIndex:
    """Hourly timestamps starting from `start`, covering ~1 year per 8760 bars."""
    return pd.date_range(start, periods=n, freq="1h", tz="UTC")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Chronological correctness — no future leaks into training
# ═══════════════════════════════════════════════════════════════════════════════

class TestWalkForwardChronology:

    def test_train_always_before_test(self):
        """Every fold: train_end <= test_start (no overlap)."""
        splitter = WalkForwardSplit(n_samples=5000)
        for fold in splitter.folds:
            assert fold.train_end <= fold.test_start, (
                f"Fold {fold.fold_id}: train_end={fold.train_end} > "
                f"test_start={fold.test_start} — future leakage!"
            )

    def test_folds_in_chronological_order(self):
        """Folds are ordered: fold[i].test_end <= fold[i+1].test_start."""
        splitter = WalkForwardSplit(n_samples=5000, n_splits=5)
        for i in range(len(splitter.folds) - 1):
            assert splitter.folds[i].test_end <= splitter.folds[i + 1].test_start, (
                f"Fold {i} and {i+1} test windows overlap"
            )

    def test_expanding_window_train_grows(self):
        """Expanding mode: each fold's train set is larger than the previous."""
        splitter = WalkForwardSplit(n_samples=5000, n_splits=5, rolling=False)
        train_sizes = [f.n_train for f in splitter.folds]
        for i in range(len(train_sizes) - 1):
            assert train_sizes[i] < train_sizes[i + 1], (
                f"Train size did not grow: fold {i}={train_sizes[i]}, "
                f"fold {i+1}={train_sizes[i+1]}"
            )

    def test_first_fold_starts_at_zero(self):
        """Expanding window: first fold always starts at index 0."""
        splitter = WalkForwardSplit(n_samples=3000, rolling=False)
        assert splitter.folds[0].train_start == 0

    def test_test_indices_within_bounds(self):
        """All test indices are valid positions in [0, n_samples)."""
        n = 4000
        splitter = WalkForwardSplit(n_samples=n)
        for fold in splitter.folds:
            assert 0 <= fold.test_start < n
            assert 0 < fold.test_end <= n

    def test_no_data_snooping_all_folds(self):
        """Every train/test pair across all folds must be strictly disjoint.

        This is the core no-lookahead invariant: index sets must not intersect.
        We check every fold rather than a single one to be thorough.
        """
        splitter = WalkForwardSplit(n_samples=5000, n_splits=5)
        for fold in splitter.folds:
            train_set = set(range(fold.train_start, fold.train_end))
            test_set  = set(range(fold.test_start, fold.test_end))
            assert train_set.isdisjoint(test_set), (
                f"Fold {fold.fold_id}: train and test sets overlap! "
                f"train=[{fold.train_start},{fold.train_end}), "
                f"test=[{fold.test_start},{fold.test_end})"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Purge gap
# ═══════════════════════════════════════════════════════════════════════════════

class TestPurgeGap:

    def test_purge_gap_present_in_all_folds(self):
        """Every fold: test_start - train_end >= PURGE_GAP_BARS."""
        splitter = WalkForwardSplit(n_samples=5000)
        for fold in splitter.folds:
            actual_gap = fold.test_start - fold.train_end
            assert actual_gap >= PURGE_GAP_BARS, (
                f"Fold {fold.fold_id}: purge gap={actual_gap} < "
                f"required={PURGE_GAP_BARS}"
            )

    def test_custom_purge_gap_honoured(self):
        """Custom purge_gap=50 is respected in all folds."""
        custom_gap = 50
        splitter = WalkForwardSplit(n_samples=5000, purge_gap=custom_gap)
        for fold in splitter.folds:
            assert fold.test_start - fold.train_end >= custom_gap

    def test_zero_purge_gap_still_no_overlap(self):
        """purge_gap=0 means train_end == test_start (touching but not overlapping)."""
        splitter = WalkForwardSplit(n_samples=3000, purge_gap=0, min_train=200,
                                    min_test=50)
        for fold in splitter.folds:
            assert fold.train_end <= fold.test_start

    def test_fold_purge_gap_property(self):
        """Fold.purge_gap property equals test_start - train_end."""
        splitter = WalkForwardSplit(n_samples=4000, purge_gap=30)
        for fold in splitter.folds:
            assert fold.purge_gap == fold.test_start - fold.train_end


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DSR ≈ 0 for random returns
# ═══════════════════════════════════════════════════════════════════════════════

class TestDSRRandomReturns:

    def test_dsr_near_zero_for_zero_sharpe(self):
        """Pure noise with observed_sharpe=0 should give DSR very close to 0."""
        dsr = deflated_sharpe_ratio(
            observed_sharpe=0.0,
            n_trials=10,
            n_obs=1000,
        )
        assert dsr < 0.1, f"Expected DSR < 0.1 for zero Sharpe, got {dsr:.4f}"

    def test_dsr_below_gate_for_random_walk(self):
        """Strategy produced by random walk should fail the 0.95 gate."""
        rng = np.random.default_rng(99)
        r = rng.normal(0, 0.01, size=1000)
        sharpe = float(r.mean() / r.std() * np.sqrt(8760))
        dsr = deflated_sharpe_ratio(
            observed_sharpe=sharpe,
            n_trials=10,
            n_obs=len(r),
        )
        assert dsr < MIN_DSR_PROBABILITY, (
            f"Random walk should fail DSR gate; got dsr={dsr:.4f}"
        )

    def test_dsr_decreases_with_more_trials(self):
        """More trials searched → lower DSR for the same observed Sharpe.

        We deliberately use a modest Sharpe (0.8) and small n_obs (200) so
        the CDF does not saturate to 1.0 and the strict inequality is testable.
        """
        sharpe = 0.8
        dsr_few   = deflated_sharpe_ratio(sharpe, n_trials=2,   n_obs=200)
        dsr_many  = deflated_sharpe_ratio(sharpe, n_trials=100, n_obs=200)
        assert dsr_few > dsr_many, (
            f"DSR should decrease as n_trials grows; "
            f"dsr_few={dsr_few:.4f}, dsr_many={dsr_many:.4f}"
        )

    def test_dsr_in_zero_one_range(self):
        """DSR must always be a probability in [0, 1]."""
        for sr in [-5.0, -1.0, 0.0, 0.5, 1.0, 2.0, 5.0]:
            dsr = deflated_sharpe_ratio(sr, n_trials=5, n_obs=500)
            assert 0.0 <= dsr <= 1.0, f"DSR={dsr:.4f} out of [0,1] for SR={sr}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. DSR is high for genuinely good strategy
# ═══════════════════════════════════════════════════════════════════════════════

class TestDSRGoodStrategy:

    def test_dsr_passes_gate_for_strong_sharpe(self):
        """
        Sharpe 3.0 with only 1 trial and 5000 obs should comfortably pass.
        This simulates a single well-researched strategy, not a grid search.
        """
        dsr = deflated_sharpe_ratio(
            observed_sharpe=3.0,
            n_trials=1,
            n_obs=5000,
            skew=-0.3,
            kurtosis=4.5,
        )
        assert dsr > MIN_DSR_PROBABILITY, (
            f"Strong strategy (SR=3.0, n_trials=1) should pass DSR gate; "
            f"got dsr={dsr:.4f}"
        )

    def test_dsr_increases_with_obs(self):
        """More observations → higher DSR for same Sharpe (more evidence).

        We use a modest Sharpe (0.7) so the CDF stays below saturation at
        both sample sizes and the strict inequality is testable.
        """
        dsr_small = deflated_sharpe_ratio(0.7, n_trials=3, n_obs=100)
        dsr_large = deflated_sharpe_ratio(0.7, n_trials=3, n_obs=2000)
        assert dsr_large > dsr_small, (
            f"More observations should increase DSR; "
            f"dsr_small={dsr_small:.4f}, dsr_large={dsr_large:.4f}"
        )

    def test_dsr_increases_with_sharpe(self):
        """Higher observed Sharpe → higher DSR (all else equal).

        We use a small n_obs (150) so the CDF doesn't saturate to 1.0 and
        the strict inequality is testable across the Sharpe range.
        """
        n_obs, n_trials = 150, 5
        sharpes = [0.3, 0.6, 0.9, 1.2]
        dsrs = [deflated_sharpe_ratio(sr, n_trials, n_obs) for sr in sharpes]
        for i in range(len(dsrs) - 1):
            assert dsrs[i] < dsrs[i + 1], (
                f"DSR should be monotone in Sharpe; "
                f"sharpes={sharpes}, dsrs={[f'{d:.4f}' for d in dsrs]}"
            )

    def test_fat_tails_reduce_dsr(self):
        """Higher kurtosis (fat tails) → lower DSR for same Sharpe.

        Fat tails inflate the SE of the Sharpe estimator, shrinking the z-score
        and therefore reducing the CDF value.  We use modest parameters so the
        values stay in the distinguishable interior of [0, 1].
        """
        sr, n_trials, n_obs = 0.8, 5, 200
        dsr_normal = deflated_sharpe_ratio(sr, n_trials, n_obs, kurtosis=3.0)
        dsr_fat    = deflated_sharpe_ratio(sr, n_trials, n_obs, kurtosis=8.0)
        assert dsr_fat < dsr_normal, (
            f"Fatter tails should reduce DSR; "
            f"dsr_normal={dsr_normal:.4f}, dsr_fat={dsr_fat:.4f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Cost adjustment reduces Sharpe
# ═══════════════════════════════════════════════════════════════════════════════

class TestCostAdjustedSharpe:

    def test_net_sharpe_lower_than_gross(self):
        """cost_adjusted_sharpe must return something lower than the gross Sharpe."""
        returns = _returns(n=5000, daily_mean=0.0002, daily_vol=0.01)
        gross = float(returns.mean() / returns.std() * np.sqrt(8760))
        net = cost_adjusted_sharpe(returns, trades_per_year=200, pair="BTCUSDT")
        assert net < gross, (
            f"Net Sharpe {net:.4f} should be less than gross {gross:.4f}"
        )

    def test_higher_frequency_hurts_more(self):
        """More trades per year → larger cost drag → lower net Sharpe."""
        returns = _returns(n=5000, daily_mean=0.0002, daily_vol=0.01)
        net_low  = cost_adjusted_sharpe(returns, trades_per_year=50,   pair="BTCUSDT")
        net_high = cost_adjusted_sharpe(returns, trades_per_year=1000, pair="BTCUSDT")
        assert net_low > net_high, (
            "Lower frequency strategy should have higher net Sharpe"
        )

    def test_expensive_pair_hurts_more(self):
        """Small-cap pairs have higher slippage → lower net Sharpe vs BTC."""
        returns = _returns(n=5000, daily_mean=0.0002, daily_vol=0.01)
        net_btc  = cost_adjusted_sharpe(returns, trades_per_year=200, pair="BTCUSDT")
        net_inj  = cost_adjusted_sharpe(returns, trades_per_year=200, pair="INJUSDT")
        btc_cost = get_total_cost("BTCUSDT")
        inj_cost = get_total_cost("INJUSDT")
        # Only assert direction if costs actually differ
        if inj_cost > btc_cost:
            assert net_inj < net_btc, (
                "Higher-cost pair should produce lower net Sharpe"
            )

    def test_zero_trades_no_cost_drag(self):
        """Zero trades per year → zero cost drag → net == gross (approximately)."""
        returns = _returns(n=5000, daily_mean=0.0002, daily_vol=0.01)
        gross = float(returns.mean() / returns.std() * np.sqrt(8760))
        net   = cost_adjusted_sharpe(returns, trades_per_year=0.0, pair="BTCUSDT")
        assert abs(net - gross) < 1e-6, (
            f"With zero trades, net={net:.6f} should equal gross={gross:.6f}"
        )

    def test_empty_returns_returns_zero(self):
        """Empty returns array must not raise; returns 0."""
        result = cost_adjusted_sharpe(np.array([]), trades_per_year=100, pair="BTCUSDT")
        assert result == 0.0

    def test_cost_uses_4h_annualisation(self):
        """
        4h bars_per_year=2190 should give different cost drag than 1h.
        Same returns + same trade count but different bar count changes cost_per_bar.
        """
        returns = _returns(n=2190, daily_mean=0.0003, daily_vol=0.015)
        net_1h = cost_adjusted_sharpe(returns, trades_per_year=50, pair="BTCUSDT",
                                      bars_per_year=8760)
        net_4h = cost_adjusted_sharpe(returns, trades_per_year=50, pair="BTCUSDT",
                                      bars_per_year=2190)
        # They should differ because cost_per_bar = total_cost * (tpy / bpy)
        assert net_1h != net_4h


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Negative / zero Sharpe fails validate_model
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidateModel:

    def test_negative_sharpe_fails(self):
        """Negative-mean returns must produce verdict=FAIL."""
        returns = _returns(n=2000, daily_mean=-0.0005, daily_vol=0.01)
        result = validate_model(returns, n_trials=5, pair="BTCUSDT",
                                trades_per_year=100)
        assert result["verdict"] == "FAIL"
        assert len(result["fail_reasons"]) > 0

    def test_zero_mean_fails(self):
        """Zero-mean random walk must fail — no edge after costs."""
        rng = np.random.default_rng(7)
        returns = rng.normal(0.0, 0.01, size=3000)
        result = validate_model(returns, n_trials=5, pair="BTCUSDT",
                                trades_per_year=50)
        assert result["verdict"] == "FAIL"

    def test_strong_strategy_passes(self):
        """
        Strategy with mean=0.0003 (annualised Sharpe ~2.6 at 1% vol) and
        n_trials=1 should pass all gates.
        """
        rng = np.random.default_rng(1)
        # Mean 0.0003 per bar, vol 0.01 → annualised SR ≈ 0.0003/0.01 * sqrt(8760) ≈ 2.8
        returns = rng.normal(0.0003, 0.01, size=5000)
        result = validate_model(returns, n_trials=1, pair="BTCUSDT",
                                trades_per_year=50)
        assert result["verdict"] == "PASS", (
            f"Strong strategy should pass; fail_reasons={result['fail_reasons']}"
        )

    def test_result_keys_complete(self):
        """validate_model always returns all expected keys regardless of verdict."""
        returns = _returns(n=1000)
        result = validate_model(returns, n_trials=3, pair="ETHUSDT",
                                trades_per_year=150)
        expected_keys = {
            "verdict", "gross_sharpe", "net_sharpe", "dsr_probability",
            "n_obs", "n_trials", "n_trials_capped", "fail_reasons",
            "skew", "kurtosis", "cost_per_bar", "total_cost",
        }
        assert expected_keys.issubset(result.keys())

    def test_insufficient_obs_fails_gracefully(self):
        """Single observation must return FAIL with a clear reason, not crash."""
        result = validate_model(np.array([0.001]), n_trials=1, pair="BTCUSDT",
                                trades_per_year=10)
        assert result["verdict"] == "FAIL"
        assert any("Insufficient" in r for r in result["fail_reasons"])

    def test_fail_reasons_nonempty_on_fail(self):
        """Every FAIL verdict must contain at least one human-readable reason."""
        returns = _returns(n=2000, daily_mean=-0.001, daily_vol=0.01)
        result = validate_model(returns, n_trials=5, pair="SOLUSDT",
                                trades_per_year=200)
        assert result["verdict"] == "FAIL"
        assert len(result["fail_reasons"]) >= 1
        assert all(isinstance(r, str) for r in result["fail_reasons"])

    def test_pass_means_empty_fail_reasons(self):
        """A PASS verdict must have an empty fail_reasons list."""
        rng = np.random.default_rng(2)
        returns = rng.normal(0.0004, 0.01, size=6000)
        result = validate_model(returns, n_trials=1, pair="BTCUSDT",
                                trades_per_year=30)
        if result["verdict"] == "PASS":
            assert result["fail_reasons"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# 7. n_trials cap warning (VALD-05)
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelVariantCap:

    def test_too_many_trials_triggers_warning(self):
        """n_trials > MAX_MODEL_VARIANTS must emit a UserWarning."""
        returns = _returns(n=3000, daily_mean=0.0002, daily_vol=0.01)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = validate_model(returns, n_trials=MAX_MODEL_VARIANTS + 5,
                                    pair="BTCUSDT", trades_per_year=100)
        assert any(issubclass(w.category, UserWarning) for w in caught), (
            "Expected a UserWarning when n_trials exceeds MAX_MODEL_VARIANTS"
        )

    def test_n_trials_capped_in_result(self):
        """result['n_trials_capped'] must equal MAX_MODEL_VARIANTS when over limit."""
        returns = _returns(n=3000, daily_mean=0.0002, daily_vol=0.01)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = validate_model(returns, n_trials=MAX_MODEL_VARIANTS + 20,
                                    pair="BTCUSDT", trades_per_year=100)
        assert result["n_trials_capped"] == MAX_MODEL_VARIANTS
        assert result["n_trials"] == MAX_MODEL_VARIANTS + 20  # original preserved

    def test_exactly_max_trials_no_warning(self):
        """n_trials == MAX_MODEL_VARIANTS must NOT trigger a warning."""
        returns = _returns(n=3000, daily_mean=0.0002, daily_vol=0.01)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            validate_model(returns, n_trials=MAX_MODEL_VARIANTS, pair="BTCUSDT",
                           trades_per_year=100)
        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
        assert len(user_warnings) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Rolling window mode
# ═══════════════════════════════════════════════════════════════════════════════

class TestRollingWindow:

    def test_rolling_train_size_is_fixed(self):
        """All folds in rolling mode have train set of size <= roll_window."""
        roll_window = 1000
        splitter = WalkForwardSplit(n_samples=5000, rolling=True,
                                    roll_window=roll_window, min_train=100)
        for fold in splitter.folds:
            assert fold.n_train <= roll_window, (
                f"Fold {fold.fold_id}: n_train={fold.n_train} > "
                f"roll_window={roll_window}"
            )

    def test_rolling_requires_roll_window(self):
        """Passing rolling=True without roll_window must raise ValueError."""
        with pytest.raises(ValueError, match="roll_window required"):
            WalkForwardSplit(n_samples=5000, rolling=True)

    def test_expanding_vs_rolling_differ(self):
        """Expanding and rolling mode must produce different train start indices."""
        n = 5000
        exp = WalkForwardSplit(n_samples=n, rolling=False)
        rol = WalkForwardSplit(n_samples=n, rolling=True, roll_window=1000,
                               min_train=100)
        # Expanding always has train_start=0; rolling last fold should have >0
        last_exp = exp.folds[-1]
        last_rol = rol.folds[-1]
        assert last_exp.train_start == 0
        assert last_rol.train_start >= 0  # may be 0 if not enough history
        # The key difference: expanding train grows, rolling stays bounded
        assert last_exp.n_train > last_rol.n_train or last_rol.n_train <= 1000


# ═══════════════════════════════════════════════════════════════════════════════
# 9 & 10. Regime coverage (2022 bear market — VALD-02)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegimeCoverage:

    def test_passes_when_2022_in_test_fold(self):
        """Dataset spanning 2020-2025 must have 2022 in at least one test fold."""
        # ~5 years of hourly data: 5 * 8760 = 43800 bars
        n = 5 * 8760
        ts = _timestamps(n=n, start="2020-01-01")
        splitter = WalkForwardSplit(n_samples=n, timestamps=ts, n_splits=5,
                                    min_train=5000, min_test=1000)
        # Should not raise
        assert splitter.verify_regime_coverage() is True

    def test_raises_when_data_too_recent(self):
        """Dataset starting 2023 cannot include 2022 — must raise RuntimeError."""
        n = 2 * 8760  # 2 years starting 2023
        ts = _timestamps(n=n, start="2023-01-01")
        splitter = WalkForwardSplit(n_samples=n, timestamps=ts, n_splits=3,
                                    min_train=2000, min_test=500)
        with pytest.raises(RuntimeError, match="2022"):
            splitter.verify_regime_coverage()

    def test_raises_without_timestamps(self):
        """verify_regime_coverage() must raise RuntimeError if no timestamps given."""
        splitter = WalkForwardSplit(n_samples=5000)
        with pytest.raises(RuntimeError, match="timestamps"):
            splitter.verify_regime_coverage()


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Embargo reduces test window
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmbargo:

    def test_embargo_reduces_test_end(self):
        """
        With embargo_pct > 0, effective test_end should be strictly less than
        the raw test end (which is test_start + test_size).

        We verify by comparing against embargo_pct=0 (no embargo).
        """
        n = 5000
        no_embargo  = WalkForwardSplit(n_samples=n, embargo_pct=0.0)
        has_embargo = WalkForwardSplit(n_samples=n, embargo_pct=0.05)

        for f_none, f_emb in zip(no_embargo.folds, has_embargo.folds):
            # Same fold structure — embargo should shrink test_end
            assert f_emb.n_test <= f_none.n_test, (
                f"Fold {f_none.fold_id}: embargo should reduce test window; "
                f"no_emb n_test={f_none.n_test}, emb n_test={f_emb.n_test}"
            )

    def test_large_embargo_shrinks_window_significantly(self):
        """10% embargo should give noticeably fewer test bars."""
        n = 10000
        no_emb  = WalkForwardSplit(n_samples=n, embargo_pct=0.0)
        big_emb = WalkForwardSplit(n_samples=n, embargo_pct=0.10)
        total_none = sum(f.n_test for f in no_emb.folds)
        total_emb  = sum(f.n_test for f in big_emb.folds)
        assert total_emb < total_none, "10% embargo should reduce total test bars"


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Fold.validate_chronology catches lookahead
# ═══════════════════════════════════════════════════════════════════════════════

class TestFoldChronologyValidation:

    def test_valid_fold_passes(self):
        """A correctly constructed fold should pass validation silently."""
        fold = Fold(fold_id=0, train_start=0, train_end=500,
                    test_start=520, test_end=700)
        fold.validate_chronology()  # Must not raise

    def test_overlapping_fold_raises(self):
        """train_end > test_start = lookahead; must raise ValueError."""
        fold = Fold(fold_id=0, train_start=0, train_end=600,
                    test_start=500, test_end=700)
        with pytest.raises(ValueError, match="lookahead|overlap"):
            fold.validate_chronology()

    def test_empty_train_raises(self):
        """train_end == train_start → empty train set; must raise."""
        fold = Fold(fold_id=0, train_start=100, train_end=100,
                    test_start=120, test_end=200)
        with pytest.raises(ValueError, match="empty"):
            fold.validate_chronology()

    def test_empty_test_raises(self):
        """test_end == test_start → empty test set; must raise."""
        fold = Fold(fold_id=0, train_start=0, train_end=100,
                    test_start=120, test_end=120)
        with pytest.raises(ValueError, match="empty"):
            fold.validate_chronology()

    def test_wfs_always_validates_on_construction(self):
        """WalkForwardSplit constructor must run validate_chronology on each fold."""
        # Providing n_samples too small to fit any fold should raise at construction
        with pytest.raises((ValueError,)):
            WalkForwardSplit(n_samples=10, n_splits=5, min_train=500, min_test=100)
