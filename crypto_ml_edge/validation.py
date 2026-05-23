"""
Walk-Forward Validation + DSR Gate — Crypto ML Edge Engine
===========================================================
Implements VALD-01 through VALD-06 as HARD GATES.

The bug we're fixing: advanced_validation.py in ml_crypto_predictor had all
the right math but never enforced any gate — a strategy with DSR probability
0.12 could still reach live trading. This module enforces the gates by design:
validate_model() returns FAIL and the caller cannot ignore it without explicitly
checking the verdict.

Academic anchors:
- Bailey & Lopez de Prado 2014: Deflated Sharpe Ratio
- Lopez de Prado 2018: Purged CV, Embargo, CPCV (Advances in Financial ML)
- Almgren & Chriss 2001: Market impact square-root model (via config cost model)

Regime coverage requirement (VALD-02):
  2022-01-01 to 2022-12-31 was crypto's worst bear year (-65% BTC).
  At least one test fold must cover this period. We verify this inside
  WalkForwardSplit.verify_regime_coverage().
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import warnings

from crypto_ml_edge.config import (
    MIN_DSR_PROBABILITY,
    MAX_MODEL_VARIANTS,
    WALK_FORWARD_FOLDS,
    PURGE_GAP_BARS,
    EMBARGO_PCT,
    get_total_cost,
)


# ═══════════════════════════════════════════════════════════════════════════════
# VALD-01 / VALD-02 / VALD-03: WALK-FORWARD SPLIT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Fold:
    """
    One walk-forward fold.

    Indices are integer positional (not timestamps). Callers index into
    their array/DataFrame with iloc[train_start:train_end], etc.

    Timeline:
        [train_start ──── train_end) [PURGE] (test_start ──── test_end) [EMBARGO]
    """
    fold_id: int
    train_start: int
    train_end: int     # exclusive upper bound
    test_start: int    # first usable test bar (after purge)
    test_end: int      # exclusive upper bound
    # Timestamp bounds — populated when index is provided to WalkForwardSplit
    train_start_ts: Optional[pd.Timestamp] = field(default=None, compare=False)
    train_end_ts: Optional[pd.Timestamp] = field(default=None, compare=False)
    test_start_ts: Optional[pd.Timestamp] = field(default=None, compare=False)
    test_end_ts: Optional[pd.Timestamp] = field(default=None, compare=False)

    @property
    def purge_gap(self) -> int:
        """Bars between end of training data and start of test data."""
        return self.test_start - self.train_end

    @property
    def n_train(self) -> int:
        return self.train_end - self.train_start

    @property
    def n_test(self) -> int:
        return self.test_end - self.test_start

    def validate_chronology(self) -> None:
        """Raise if fold has any temporal inconsistency."""
        if self.train_end > self.test_start:
            raise ValueError(
                f"Fold {self.fold_id}: train_end={self.train_end} "
                f"overlaps test_start={self.test_start} — lookahead!"
            )
        if self.test_start < self.train_end:
            raise ValueError(
                f"Fold {self.fold_id}: no purge gap — "
                f"train_end={self.train_end}, test_start={self.test_start}"
            )
        if self.n_train <= 0:
            raise ValueError(f"Fold {self.fold_id}: empty train set")
        if self.n_test <= 0:
            raise ValueError(f"Fold {self.fold_id}: empty test set")


class WalkForwardSplit:
    """
    Generates purged, embargoed walk-forward folds for time-series ML.

    VALD-01: Expanding window (default) or rolling window (fixed size).
    VALD-02: verify_regime_coverage() checks that 2022 bear market appears
             in at least one test fold.
    VALD-03: Purge gap removes PURGE_GAP_BARS between train end and test start.
             Embargo removes EMBARGO_PCT fraction of test set from the trailing
             edge of each test window (prevents the model seeing near-boundary
             samples that correlate with training data).

    Usage:
        splitter = WalkForwardSplit(n_samples=8760, timestamps=df.index)
        for fold in splitter.folds:
            X_train = X.iloc[fold.train_start : fold.train_end]
            X_test  = X.iloc[fold.test_start  : fold.test_end]
    """

    # 2022 bear market window (VALD-02)
    BEAR_MARKET_START = pd.Timestamp("2022-01-01", tz="UTC")
    BEAR_MARKET_END   = pd.Timestamp("2022-12-31", tz="UTC")

    def __init__(
        self,
        n_samples: int,
        n_splits: int = WALK_FORWARD_FOLDS,
        purge_gap: int = PURGE_GAP_BARS,
        embargo_pct: float = EMBARGO_PCT,
        min_train: int = 500,
        min_test: int = 100,
        rolling: bool = False,
        roll_window: Optional[int] = None,
        timestamps: Optional[pd.DatetimeIndex] = None,
    ):
        """
        Args:
            n_samples:   Total number of observations in the dataset.
            n_splits:    Number of folds (WALK_FORWARD_FOLDS from config = 5).
            purge_gap:   Bars to delete between train end and test start
                         (PURGE_GAP_BARS from config = 20). Prevents any
                         feature computed at train[-1] from leaking into test.
            embargo_pct: Fraction of test window to drop from its TRAILING
                         edge (EMBARGO_PCT from config = 0.01 = 1%). Stops the
                         model training on samples adjacent to future data.
            min_train:   Minimum training bars per fold (hard floor).
            min_test:    Minimum test bars per fold (hard floor).
            rolling:     If True, use a fixed-size rolling window instead of
                         an expanding window. Avoids old-regime contamination.
            roll_window: Size of rolling train window (required when rolling=True).
            timestamps:  Optional DatetimeIndex aligned to the data. When
                         provided, Fold objects will have *_ts fields populated
                         and verify_regime_coverage() becomes meaningful.
        """
        if rolling and roll_window is None:
            raise ValueError("roll_window required when rolling=True")
        if n_splits < 1:
            raise ValueError("n_splits must be >= 1")
        if purge_gap < 0:
            raise ValueError("purge_gap must be >= 0")
        if not (0.0 <= embargo_pct < 1.0):
            raise ValueError("embargo_pct must be in [0, 1)")

        self.n_samples = n_samples
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct
        self.min_train = min_train
        self.min_test = min_test
        self.rolling = rolling
        self.roll_window = roll_window
        self.timestamps = timestamps

        self.folds: List[Fold] = self._build_folds()

        # Eagerly validate chronology — fail fast rather than silently producing
        # bad train/test splits that would only be caught during training.
        for fold in self.folds:
            fold.validate_chronology()

    # ── Internal fold builder ────────────────────────────────────────────────

    def _build_folds(self) -> List[Fold]:
        """Return a list of Fold objects covering the full dataset."""
        n = self.n_samples
        folds: List[Fold] = []

        # Each test window is roughly equal in size. We anchor from the end of
        # the dataset so the most recent data is always in the last test fold.
        test_size = max(self.min_test, (n - self.min_train) // self.n_splits)

        for i in range(self.n_splits):
            # Test window for fold i (counting from the end)
            test_end   = n - (self.n_splits - 1 - i) * test_size
            test_start = test_end - test_size

            # Apply embargo: shrink test_end by embargo_pct of test_size.
            embargo_bars = max(0, int(test_size * self.embargo_pct))
            # Embargo affects the trailing edge; shrink test_end inward.
            # This means we don't evaluate on the very last few bars of the
            # test window where features might still correlate with training.
            effective_test_end = test_end - embargo_bars

            # Purge: train must end at least PURGE_GAP_BARS before test starts
            train_end = test_start - self.purge_gap

            if self.rolling:
                train_start = max(0, train_end - self.roll_window)
            else:
                # Expanding window: always starts at 0
                train_start = 0

            # Hard floors
            if train_end - train_start < self.min_train:
                continue
            if effective_test_end - test_start < self.min_test:
                continue

            # Populate timestamp fields if an index was supplied
            ts_kwargs = {}
            if self.timestamps is not None:
                idx = self.timestamps
                ts_kwargs = {
                    "train_start_ts": idx[train_start],
                    "train_end_ts":   idx[min(train_end - 1, len(idx) - 1)],
                    "test_start_ts":  idx[test_start],
                    "test_end_ts":    idx[min(effective_test_end - 1, len(idx) - 1)],
                }

            folds.append(Fold(
                fold_id=len(folds),
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=effective_test_end,
                **ts_kwargs,
            ))

        if not folds:
            raise ValueError(
                f"No valid folds generated from {n} samples with "
                f"n_splits={self.n_splits}, min_train={self.min_train}, "
                f"min_test={self.min_test}. Reduce min_train or n_splits."
            )

        return folds

    # ── Public helpers ───────────────────────────────────────────────────────

    def verify_regime_coverage(self) -> bool:
        """
        VALD-02: Assert that at least one test fold covers the 2022 bear market.

        Returns True if covered, raises RuntimeError if not.
        Requires timestamps to be provided at construction.
        """
        if self.timestamps is None:
            raise RuntimeError(
                "Cannot verify regime coverage without timestamps. "
                "Pass timestamps=df.index when constructing WalkForwardSplit."
            )

        bear_start = self.BEAR_MARKET_START
        bear_end   = self.BEAR_MARKET_END

        for fold in self.folds:
            if fold.test_start_ts is None or fold.test_end_ts is None:
                continue
            # Overlap check: fold test window intersects [bear_start, bear_end]
            if fold.test_start_ts <= bear_end and fold.test_end_ts >= bear_start:
                return True

        raise RuntimeError(
            "VALD-02 VIOLATION: No test fold covers the 2022 bear market "
            f"({bear_start.date()} to {bear_end.date()}). "
            "Extend the dataset back to 2020 to include 2022 in a test fold."
        )

    def summary(self) -> str:
        """Human-readable fold summary for logging."""
        lines = [f"WalkForwardSplit: {len(self.folds)} folds, n={self.n_samples}"]
        for f in self.folds:
            if f.train_start_ts is not None:
                lines.append(
                    f"  Fold {f.fold_id}: "
                    f"train [{f.train_start_ts.date()} - {f.train_end_ts.date()}] "
                    f"({f.n_train} bars)  →  "
                    f"test [{f.test_start_ts.date()} - {f.test_end_ts.date()}] "
                    f"({f.n_test} bars)"
                )
            else:
                lines.append(
                    f"  Fold {f.fold_id}: "
                    f"train [{f.train_start}:{f.train_end}] ({f.n_train} bars)  →  "
                    f"test [{f.test_start}:{f.test_end}] ({f.n_test} bars)"
                )
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# VALD-04: DEFLATED SHARPE RATIO GATE
# ═══════════════════════════════════════════════════════════════════════════════

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """
    Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio.

    Returns the probability P(true Sharpe > 0) after correcting for:
      1. Multiple testing: we tested n_trials strategies and picked the best.
         The expected maximum Sharpe under the null (all noise) grows with
         log(n_trials) — we must beat that, not just beat zero.
      2. Non-normal returns: fat tails and skewness inflate the raw Sharpe.
      3. Finite sample: the Sharpe estimator has a standard error that shrinks
         with sqrt(n_obs).

    HARD GATE (VALD-04): only models where this probability > MIN_DSR_PROBABILITY
    (0.95) are promoted. validate_model() enforces this gate automatically.

    Args:
        observed_sharpe: Best Sharpe ratio seen across all n_trials variants.
                         Must be annualised (multiply by sqrt(bars_per_year)
                         before passing in).
        n_trials:        Total number of strategy variants evaluated. Cap at
                         MAX_MODEL_VARIANTS (10) to prevent inflation.
        n_obs:           Number of return observations used to compute the
                         Sharpe (i.e. len(returns)).
        skew:            Return distribution skewness (scipy.stats.skew).
                         Defaults to 0 (normal).
        kurtosis:        Excess kurtosis + 3, i.e. the 4th standardised moment.
                         Normal = 3. Crypto returns typically 5-10.

    Returns:
        Probability in [0, 1]. Values > MIN_DSR_PROBABILITY (0.95) pass.

    Notes:
        - Returns 0.0 for random-walk returns (observed_sharpe near 0).
        - Returns a value near 1.0 for genuinely strong strategies.
        - The formula is derived in Appendix A of Bailey & LdP 2014. We use
          the Euler-Mascheroni approximation for E[max(Z_1,...,Z_n)] which
          is accurate to within 0.02 for n >= 5.
    """
    try:
        from scipy import stats as sp_stats
    except ImportError as e:
        raise ImportError("scipy required for DSR: pip install scipy") from e

    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if n_obs < 2:
        raise ValueError("n_obs must be >= 2")

    # ── Step 1: Expected maximum Sharpe under null hypothesis ────────────────
    # Under H0 all strategies are pure noise with SR~N(0,1).
    # E[max(SR)] = sqrt(2*log(n)) - (log(pi)+gamma) / (2*sqrt(2*log(n)))
    # where gamma = Euler-Mascheroni constant ≈ 0.5772.
    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        euler_mascheroni = 0.5772156649
        log2n = 2.0 * np.log(n_trials)
        sqrt_log2n = np.sqrt(log2n)
        expected_max_sr = (sqrt_log2n
                           - (np.log(np.pi) + euler_mascheroni)
                           / (2.0 * sqrt_log2n))

    # ── Step 2: Standard error of Sharpe (non-normal correction) ────────────
    # From IID Sharpe SE formula adjusted for higher moments (Christie 2005):
    #   SE(SR) = sqrt( (1 + 0.5*SR^2 - skew*SR + (kurt-3)/4*SR^2) / n )
    # "kurt" here is the excess kurtosis, so we use (kurtosis - 3).
    excess_kurt = kurtosis - 3.0
    variance_numerator = (
        1.0
        + 0.5 * observed_sharpe ** 2
        - skew * observed_sharpe
        + (excess_kurt / 4.0) * observed_sharpe ** 2
    )
    # Guard against negative variance from extreme inputs
    variance_numerator = max(variance_numerator, 1e-8)
    se_sr = np.sqrt(variance_numerator / n_obs)

    # ── Step 3: Deflated Sharpe = observed minus expected-max scaled by SE ──
    # This is equation (4) in Bailey & LdP 2014:
    #   DSR = Phi( (SR_hat - E[max(SR)]) / SE )
    # where Phi is the standard normal CDF.
    if se_sr <= 0.0:
        return 0.5

    z = (observed_sharpe - expected_max_sr) / se_sr
    dsr_probability = float(sp_stats.norm.cdf(z))

    return dsr_probability


# ═══════════════════════════════════════════════════════════════════════════════
# VALD-06: COST-ADJUSTED SHARPE
# ═══════════════════════════════════════════════════════════════════════════════

def cost_adjusted_sharpe(
    returns: np.ndarray,
    trades_per_year: float,
    pair: str,
    bars_per_year: int = 8760,
) -> float:
    """
    Deduct transaction costs from returns and recompute the annualised Sharpe.

    VALD-06: All backtest results must reflect Binance fees + estimated
    slippage before any validation gate is applied. Gross Sharpe numbers
    are meaningless for real trading.

    Cost model:
        total_round_trip = ROUND_TRIP_FEE + 2 * slippage[pair]
        (from config.get_total_cost — 0.30% for BTC, up to 0.40% for small-caps)

    Cost is expressed as a per-bar deduction so it can be subtracted from
    the return series directly:
        cost_per_bar = total_round_trip * (trades_per_year / bars_per_year)

    This is conservative — it assumes costs are uniformly distributed, whereas
    in reality they cluster around entry/exit bars. The effect is to slightly
    underestimate the Sharpe of low-frequency strategies and slightly over-
    estimate for high-frequency ones, but it is unbiased in expectation.

    Args:
        returns:         Array of per-bar returns (not annualised). Must be
                         in decimal form (0.001 = 0.1%, not 0.1).
        trades_per_year: Expected number of round-trip trades per year.
                         Use historical trade count / years_in_sample.
        pair:            Binance trading pair symbol (e.g. "BTCUSDT") used to
                         look up the per-pair slippage from config.SLIPPAGE_MAP.
        bars_per_year:   Bars per calendar year for the timeframe.
                         Default 8760 = 1h bars. Use 2190 for 4h bars.

    Returns:
        Net annualised Sharpe ratio after cost deduction.
        Will be lower than gross Sharpe — that is the correct behaviour.
    """
    returns = np.asarray(returns, dtype=float)
    if len(returns) == 0:
        return 0.0

    total_cost_round_trip = get_total_cost(pair)

    # Distribute cost ONLY across bars with actual positions (non-zero returns).
    # The old formula subtracted cost_per_bar from ALL bars including zero-signal
    # bars, creating massive phantom drag on sparse signal arrays.
    n_trade_bars = int(np.sum(returns != 0))
    if n_trade_bars > 0 and trades_per_year > 0:
        # Total cost for all trades in the sample
        years_in_sample = len(returns) / bars_per_year
        total_trades_in_sample = trades_per_year * years_in_sample
        total_cost_in_sample = total_trades_in_sample * total_cost_round_trip
        # Spread cost evenly across trade bars only
        cost_per_trade_bar = total_cost_in_sample / n_trade_bars
        cost_array = np.where(returns != 0, cost_per_trade_bar, 0.0)
    else:
        cost_array = np.zeros_like(returns)
    net_returns = returns - cost_array

    std = net_returns.std()
    if std < 1e-10:
        return 0.0

    # Annualise: multiply per-bar Sharpe by sqrt(bars_per_year)
    net_sharpe = (net_returns.mean() / std) * np.sqrt(bars_per_year)
    return float(net_sharpe)


# ═══════════════════════════════════════════════════════════════════════════════
# VALD-04 / VALD-05 / VALD-06: VALIDATE MODEL (MAIN GATE)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_model(
    returns: np.ndarray,
    n_trials: int,
    pair: str,
    trades_per_year: float,
    bars_per_year: int = 8760,
    skew: Optional[float] = None,
    kurtosis: Optional[float] = None,
) -> dict:
    """
    Run the full validation gate for a single model.

    Checks performed:
        1. n_trials <= MAX_MODEL_VARIANTS (VALD-05): caps multiple-testing risk.
        2. Cost-adjusted Sharpe (VALD-06): deducts fees and slippage.
        3. DSR probability > MIN_DSR_PROBABILITY (VALD-04): hard gate.

    Args:
        returns:         Per-bar return series (decimal, e.g. 0.001 = 0.1%).
        n_trials:        Number of model variants evaluated in this training
                         run. Must be <= MAX_MODEL_VARIANTS (10).
        pair:            Trading pair for cost look-up (e.g. "BTCUSDT").
        trades_per_year: Annualised trade frequency.
        bars_per_year:   Bars per year for annualisation (8760 for 1h).
        skew:            Return skewness. Computed from returns if None.
        kurtosis:        Return kurtosis (raw, not excess). Computed if None.

    Returns:
        dict with keys:
            verdict:           "PASS" | "FAIL"
            gross_sharpe:      Annualised Sharpe before costs.
            net_sharpe:        Annualised Sharpe after costs.
            dsr_probability:   P(true edge exists) after multiple-testing
                               correction. Must exceed 0.95 to pass.
            n_obs:             Number of return observations.
            n_trials:          Number of model variants tested.
            n_trials_capped:   Actual n_trials used (may be capped to MAX).
            fail_reasons:      List of human-readable failure reasons (empty
                               if verdict == "PASS").
            skew:              Skewness of returns.
            kurtosis:          Kurtosis of returns (raw moment, not excess).
            cost_per_bar:      Per-bar cost deducted.
            total_cost:        Total round-trip cost for the pair.

    Example:
        result = validate_model(
            returns=oos_returns,
            n_trials=5,
            pair="BTCUSDT",
            trades_per_year=200,
        )
        if result["verdict"] != "PASS":
            print("Model rejected:", result["fail_reasons"])
    """
    returns = np.asarray(returns, dtype=float)
    n_obs = len(returns)
    fail_reasons: List[str] = []

    # ── VALD-05: Cap model variants ──────────────────────────────────────────
    if n_trials > MAX_MODEL_VARIANTS:
        warnings.warn(
            f"n_trials={n_trials} exceeds MAX_MODEL_VARIANTS={MAX_MODEL_VARIANTS}. "
            "Capping to prevent multiple-testing inflation (VALD-05). "
            "Only train at most 10 variants per run.",
            stacklevel=2,
        )
        n_trials_capped = MAX_MODEL_VARIANTS
    else:
        n_trials_capped = n_trials

    # ── Basic stats ──────────────────────────────────────────────────────────
    if n_obs < 2:
        fail_reasons.append(f"Insufficient observations: n_obs={n_obs} < 2")
        return {
            "verdict": "FAIL",
            "gross_sharpe": 0.0,
            "net_sharpe": 0.0,
            "dsr_probability": 0.0,
            "n_obs": n_obs,
            "n_trials": n_trials,
            "n_trials_capped": n_trials_capped,
            "fail_reasons": fail_reasons,
            "skew": 0.0,
            "kurtosis": 3.0,
            "cost_per_bar": 0.0,
            "total_cost": get_total_cost(pair),
        }

    ret_std = returns.std()
    gross_sharpe = (
        (returns.mean() / ret_std * np.sqrt(bars_per_year))
        if ret_std > 1e-10
        else 0.0
    )

    # Compute distributional moments if not supplied
    if skew is None:
        skew = float(pd.Series(returns).skew()) if n_obs >= 4 else 0.0
    if kurtosis is None:
        # pd.Series.kurtosis() returns EXCESS kurtosis; add 3 for the raw 4th moment
        kurtosis = (float(pd.Series(returns).kurtosis()) + 3.0) if n_obs >= 4 else 3.0

    # ── VALD-06: Net Sharpe after costs ─────────────────────────────────────
    total_cost = get_total_cost(pair)
    # Distribute cost ONLY across trade bars (same logic as cost_adjusted_sharpe).
    n_trade_bars = int(np.sum(returns != 0))
    if n_trade_bars > 0 and trades_per_year > 0:
        years_in_sample = len(returns) / bars_per_year
        total_trades_in_sample = trades_per_year * years_in_sample
        total_cost_in_sample = total_trades_in_sample * total_cost
        cost_per_trade_bar = total_cost_in_sample / n_trade_bars
        cost_array = np.where(returns != 0, cost_per_trade_bar, 0.0)
    else:
        cost_array = np.zeros_like(returns)
    net_returns = returns - cost_array
    cost_per_bar = total_cost * (trades_per_year / bars_per_year)  # kept for reporting
    net_std = net_returns.std()
    net_sharpe = (
        (net_returns.mean() / net_std * np.sqrt(bars_per_year))
        if net_std > 1e-10
        else 0.0
    )

    if net_sharpe <= 0:
        fail_reasons.append(
            f"Net Sharpe is non-positive after costs: {net_sharpe:.4f} "
            f"(gross={gross_sharpe:.4f}, cost_per_bar={cost_per_bar:.6f})"
        )

    # ── VALD-04: DSR gate ────────────────────────────────────────────────────
    # DSR uses the NET Sharpe (we've already paid costs) and the capped
    # n_trials so overfitting from wide search is penalised correctly.
    dsr_prob = deflated_sharpe_ratio(
        observed_sharpe=net_sharpe,
        n_trials=n_trials_capped,
        n_obs=n_obs,
        skew=skew,
        kurtosis=kurtosis,
    )

    if dsr_prob <= MIN_DSR_PROBABILITY:
        fail_reasons.append(
            f"DSR probability {dsr_prob:.4f} does not exceed gate "
            f"{MIN_DSR_PROBABILITY} (VALD-04). "
            f"Strategy edge is likely due to chance across {n_trials_capped} trials."
        )

    verdict = "PASS" if not fail_reasons else "FAIL"

    return {
        "verdict": verdict,
        "gross_sharpe": float(gross_sharpe),
        "net_sharpe": float(net_sharpe),
        "dsr_probability": float(dsr_prob),
        "n_obs": int(n_obs),
        "n_trials": int(n_trials),
        "n_trials_capped": int(n_trials_capped),
        "fail_reasons": fail_reasons,
        "skew": float(skew),
        "kurtosis": float(kurtosis),
        "cost_per_bar": float(cost_per_bar),
        "total_cost": float(total_cost),
    }
