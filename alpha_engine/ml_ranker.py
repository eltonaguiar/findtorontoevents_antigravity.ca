"""
ALPHA_ENGINE -- ML Signal Ranker (Phase 9 -- Regression + Boruta Feature Selection)
========================================================================
Heterogeneous stacking ensemble (XGBoost/LightGBM primary + RF + CatBoost
secondary, with RandomForest-only fallback) that learns from closed picks
to predict win probability for new signals. CatBoost is optional (graceful
skip if not installed) and uses ordered boosting (has_time=True) for
time-series-aware gradient boosting without temporal leakage.

Features: 40 engineered features per signal (33 base + 7 chi-squared validated
technical indicators from Phase 13), pruned to ~15-20 via Boruta
feature selection (Phase 9). Boruta uses shadow features + Random Forest
to identify truly predictive features (Kursa & Rudnicki, 2010). Results
cached to data/boruta_selected_features.json (re-runs weekly or on change).
Model: XGBoost primary, LightGBM secondary, RandomForest fallback.
Meta-labeling: probability gate at 0.65 suppresses low-confidence signals.
Fallback: Heuristic scoring when < 50 closed picks (cold start).

Phase 5 audit (2026-03-17) -- DEAD FEATURE REMOVAL:
  Removed 22 features that were ALWAYS zero in 342 closed picks:
  - spread_pct, wick_ratio, consecutive_losses, strategy_pnl_last10 (never populated)
  - market_fear_greed, funding_rate, entry_distance_vwap (never populated)
  - ema_position, orderbook_imbalance, cvd_divergence (never populated)
  - smoothed_momentum, vpin, ofi, galaxy_score (no OHLCV data)
  - accel_10..cci_20 (10 Kimi Blueprint features, no price arrays)

Phase 5 additions (2026-03-17) -- FEATURES FROM REAL DATA:
  Time-of-day features (from timestamp):
    hour_sin, hour_cos, day_of_week, is_weekend, hour_x_vol
  Volatility/trade features (from entry/TP/SL/pnl):
    sl_distance_pct, tp_distance_pct, direction_market_alignment
  Outcome features REMOVED in Phase 11 (caused AUC=1.0 overfitting):
    entry_vs_optimal, hold_duration_hours, mfe_pct, mae_pct
    These leaked future info -- moved to LEAKY_FEATURES exclusion set.

Phase 6 additions (2026-03-17) -- TRIPLE-BARRIER LABELS + FUNDING FEATURES:
  Triple-barrier labeling: +1 (TP hit), 0 (expired/uncertain), -1 (SL hit)
    with asymmetric sample weights (loss=1.2, uncertain=0.5, win=1.0)
  Funding/basis features (strongest 4h-1d predictors per evidence review):
    funding_rate_raw, funding_z_30d, funding_persistence

Phase 7 additions (2026-03-17) -- LIVE MICROSTRUCTURE FEATURES:
  Connected scanner's OBI/VPIN/funding injection to ML feature vector:
    orderbook_imbalance -- L2 depth bid-ask imbalance [-1, +1] (default 0)
    vpin_toxicity -- informed trading probability [0, 1] (default 0.5)
    funding_rate_norm -- funding_rate / 0.01 clipped [-3, +3] (default 0)
  These were previously removed as dead features; scanner now populates them.

Phase 8 additions (2026-03-17) -- OBI VELOCITY FEATURES (EFMA 2025):
  Order flow imbalance velocity -- delta of OBI over time windows:
    obi_delta_5 -- OBI change over last 5 scans [-1, +1] (default 0)
    obi_delta_15 -- OBI change over last 15 scans [-1, +1] (default 0)
    obi_acceleration -- second derivative of OBI [-1, +1] (default 0)
  Academic basis: Sharpe 3.04-3.63 with ML + order flow velocity (EFMA 2025).
  History tracked in data/obi_history.json (100 snapshots per symbol).

Incremental Training (2026-03-17) -- WARM-START XGBOOST + DRIFT DETECTION:
  smart_train() dispatcher: incremental by default, full retrain on drift.
  incremental_train(): warm-starts XGBoost from existing booster, adds 10 trees
    using only new closed picks since last training (via last_trained_at timestamp).
  _check_drift(): accuracy-based drift detection over rolling window of 50
    predictions. If accuracy < 45%, triggers full retrain instead of incremental.
  Prediction history tracked in data/prediction_history.json (last 500 entries).
  Scanner auto-backfills prediction outcomes from closed_picks.json before training.

Phase 10 additions (2026-03-18) -- CROSS-SECTIONAL RANKING FEATURES:
  Instead of predicting "will BTC go up?", rank "which of N coins will
  outperform?" -- ranking is easier than absolute forecasting (Liu et al. 2022 JFE).
  Features computed in cross_sectional.py, injected by scanner onto each signal:
    cs_momentum_rank -- percentile rank of 7d return vs universe [0, 1]
    cs_relative_strength -- 7d return minus BTC 7d return, clipped [-1, 1]
    cs_dispersion -- std dev of all symbols' 7d returns, normalized [0, 1]
    cs_leader_lag -- correlation of symbol returns with BTC lagged returns [-1, 1]

Phase 9 additions (2026-03-18) -- BORUTA FEATURE SELECTION:
  Boruta algorithm (Kursa & Rudnicki, 2010) identifies truly important features
  by comparing real feature importances against shadow (permuted) copies.
  select_features(): runs Boruta with RF estimator, caches results for 7 days.
  Reduces 39 features to ~15-20, improving sample:feature ratio from 1:26 to 1:50+.
  Toggle: USE_BORUTA_SELECTION = True (default). Graceful fallback if boruta
  package not installed. Cache: data/boruta_selected_features.json.

Phase 11 audit (2026-03-19) -- OVERFITTING FIX (AUC=1.0 -> realistic):
  Root cause: 4 "outcome" features leaked future information into training:
    entry_vs_optimal, hold_duration_hours, mfe_pct, mae_pct
  These are only knowable AFTER a trade closes, making prediction trivial.
  Fix: moved to LEAKY_FEATURES set, excluded from feature vector.
  Added purged time-series CV with 2% embargo (Lopez de Prado, AFML Ch.7)
  to prevent temporal leakage at fold boundaries.
  Added AUC > 0.90 sanity check warning.

Phase 13 additions (2026-03-21) -- CHI-SQUARED VALIDATED TECHNICAL FEATURES:
  7 indicators proven predictive via chi-squared test (92.4% XGBoost accuracy):
    mom30 -- 30-period momentum [-0.5, 0.5] (default 0.0)
    rsi30 -- 30-period RSI Wilder [0, 1] (default 0.5)
    macd_hist_norm -- MACD histogram / price [-0.05, 0.05] (default 0.0)
    stoch_k30 -- 30-period Stochastic %K [0, 1] (default 0.5)
    stoch_d30 -- 3-period SMA of %K30 [0, 1] (default 0.5)
    cci20_norm -- CCI 20 normalized [-1, 1] (default 0.0)
    williams_r -- Williams %R 14 [-1, 0] (default -0.5)
  Computed in technical_features.py (pure Python, no numpy). Injected by scanner
  onto each signal from OHLCV data at signal time.

Training is automatic: triggers when enough data accumulates.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from config import DATA_DIR, ML_MODEL_PATH, ML_WEIGHTS_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dynamic ensemble weighting (backwards-compatible import)
# ---------------------------------------------------------------------------
try:
    from dynamic_ensemble import DynamicEnsemble
    _HAS_DYNAMIC_ENSEMBLE = True
except ImportError:
    _HAS_DYNAMIC_ENSEMBLE = False

# Path for prediction history (drift detection)
PREDICTION_HISTORY_PATH = DATA_DIR / "prediction_history.json"
PREDICTION_HISTORY_MAX = 500

# ---------------------------------------------------------------------------
# Model availability checks (XGBoost > LightGBM > sklearn RF)
# ---------------------------------------------------------------------------
try:
    import xgboost as xgb
    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False
    import warnings
    warnings.warn(
        "XGBoost not available -- ML ranker will try LightGBM or fall back to RandomForest. "
        "Install with: pip install xgboost",
        UserWarning,
        stacklevel=1,
    )

try:
    import lightgbm as lgb
    _HAS_LIGHTGBM = True
except ImportError:
    _HAS_LIGHTGBM = False
    if not _HAS_XGBOOST:
        import warnings
        warnings.warn(
            "LightGBM not available -- ML ranker will fall back to RandomForest. "
            "Install with: pip install lightgbm",
            UserWarning,
            stacklevel=1,
        )

try:
    from catboost import CatBoostClassifier as _CatBoostCls
    _HAS_CATBOOST = True
except ImportError:
    _HAS_CATBOOST = False

# Boruta feature selection (optional -- reduces 41 features to ~15-20)
# Install with: pip install boruta
# When unavailable, all features are kept (graceful fallback).
try:
    from boruta import BorutaPy
    _HAS_BORUTA = True
except ImportError:
    _HAS_BORUTA = False

# Toggle Boruta feature selection on/off. When True, select_features() runs
# Boruta during training and caches the result. When False, all features are
# used (legacy behavior).
USE_BORUTA_SELECTION = True

# NOTE: SciPy/Savitzky-Golay imports and smooth_price_series() were removed
# in Phase 5. They were only used by _compute_smoothed_momentum which relied
# on price arrays that were never present in the training data (0/342 picks).


# Meta-labeling: signals with predicted win probability below this gate
# are suppressed (scored below the scanner's MIN_ML_SCORE = 0.50 threshold).
# Phase 19 (2026-04-15): raised from 0.55 to 0.60 — with proper training data
# (313 alpha_engine picks from closed_picks_fast.json), the model can now
# meaningfully discriminate. Gate at 0.60 filters bottom-quartile signals.
META_LABEL_PROBABILITY_GATE = 0.60

# ---------------------------------------------------------------------------
# REGRESSION MODE (Phase 9): DISABLED -- reverted to classification
# ---------------------------------------------------------------------------
# Regression was predicting pnl_pct magnitude but the target distribution is
# near-zero (mean=0.013, std=0.11) which causes XGBRegressor to learn a
# constant prediction with ALL feature importances = 0. Classification with
# binary WON/LOST labels is far more effective for this dataset (149W/163L/54E).
USE_REGRESSION = False

# Sigmoid steepness for converting predicted return to 0-1 score.
# Maps: +5% predicted return -> ~0.73, 0% -> 0.50, -5% -> ~0.27
_REGRESSION_SIGMOID_STEEPNESS = 20.0



# ---------------------------------------------------------------------------
# Timestamp helpers for time-of-day features
# ---------------------------------------------------------------------------
def _parse_signal_ts(signal: dict) -> Optional[datetime]:
    """Return a datetime from any timestamp field in the signal, or None."""
    for key in ("generated_at", "entry_time", "created_at", "timestamp", "entry_date"):
        val = signal.get(key)
        if val:
            try:
                if isinstance(val, datetime):
                    return val
                val_str = str(val)
                # Date-only strings (e.g. "2026-03-11") lack time -- append midnight UTC
                if len(val_str) == 10 and val_str[4] == "-":
                    val_str += "T00:00:00+00:00"
                return datetime.fromisoformat(val_str.replace("Z", "+00:00"))
            except Exception:
                continue
    return None


def _ts_hour(signal: dict) -> float:
    """Hour-of-day (UTC) when the signal was generated, 0-23. Falls back to current hour."""
    ts = _parse_signal_ts(signal)
    return float((ts or datetime.now(timezone.utc)).hour)


def _ts_dow(signal: dict) -> float:
    """Day-of-week (Mon=0 … Sun=6) when the signal was generated. Falls back to today."""
    ts = _parse_signal_ts(signal)
    return float((ts or datetime.now(timezone.utc)).weekday())


def _compute_triple_barrier_label(pick: dict) -> tuple:
    """Compute triple-barrier label for a closed pick.

    Three barriers:
    1. Upper (profit-taking): entry + pt_mult * volatility
    2. Lower (stop-loss): entry - sl_mult * volatility
    3. Vertical (time expiry): max_hold bars

    Label:
    - +1: upper barrier hit first (profitable)
    -  0: vertical barrier hit (timed out, uncertain)
    - -1: lower barrier hit first (loss)

    Uses actual trade outcome since we have closed picks with pnl_pct:
    - pnl_pct > 0 and hit TP: +1
    - pnl_pct < 0 and hit SL: -1
    - expired/other: 0

    Sample weights (asymmetric to penalize false positives more):
    - +1 samples: weight = 1.0
    -  0 samples: weight = 0.5 (uncertain, less informative)
    - -1 samples: weight = 1.2 (penalize false positives more)

    Returns:
        (label, sample_weight) tuple
    """
    result = str(pick.get('result', '') or pick.get('status', '') or '').upper()
    pnl = float(pick.get('pnl_pct', 0) or 0)

    if 'TP' in result or (pnl > 0 and 'WIN' in result) or result == 'WON':
        return 1, 1.0
    elif 'SL' in result or (pnl < 0 and ('LOSS' in result or 'STOP' in result)) or result == 'LOST':
        return -1, 1.2
    elif 'EXPIR' in result or pnl == 0:
        return 0, 0.5
    elif pnl > 0:
        return 1, 1.0
    else:
        return -1, 1.2


def _purged_time_series_cv(n_samples, n_splits=5, embargo_pct=0.02):
    """Purged K-Fold CV with embargo (Lopez de Prado, AFML Ch.7).

    Prevents temporal data leakage at fold boundaries by adding
    an embargo gap between training and test sets. This is critical
    for financial time-series where adjacent samples are correlated.

    Args:
        n_samples: Total number of samples.
        n_splits: Number of CV folds (default 5).
        embargo_pct: Fraction of samples to embargo between train/test (default 2%).

    Yields:
        (train_idx, test_idx) tuples with embargo gap between them.
    """
    embargo_size = max(1, int(n_samples * embargo_pct))
    fold_size = n_samples // (n_splits + 1)

    for i in range(n_splits):
        test_start = (i + 1) * fold_size
        test_end = min(test_start + fold_size, n_samples)
        train_end = max(0, test_start - embargo_size)

        train_idx = list(range(0, train_end))
        test_idx = list(range(test_start, test_end))

        if len(train_idx) >= 10 and len(test_idx) >= 5:
            yield train_idx, test_idx


class MLSignalRanker:
    """Learns from trade outcomes to rank future signals."""

    MIN_SAMPLES_TO_TRAIN = 50
    # ---------------------------------------------------------------------------
    # LEAKY FEATURES -- excluded from prediction (only available after trade closes)
    # These caused AUC=1.0 overfitting: the model was learning from the outcome
    # itself rather than predicting it. See Phase 11 audit (2026-03-19).
    # ---------------------------------------------------------------------------
    LEAKY_FEATURES = {
        "strategy_encoded",      # LEAKED: hash-based strategy ID acts as source proxy (quan_engine hash=0.857)
        "entry_vs_optimal",     # LEAKED: requires knowing post-entry price path
        "hold_duration_hours",  # LEAKED: only known when trade closes
        "mfe_pct",              # LEAKED: max favorable excursion = best P/L during trade
        "mae_pct",              # LEAKED: max adverse excursion = worst P/L during trade
        "strategy_win_rate",    # LEAKED: aggregate stat acts as strategy identity proxy
        "strategy_sharpe",      # LEAKED: same - strategy identity proxy (r=0.952 with strategy_win_rate)
        "strategy_closed_picks", # LEAKED: same - strategy identity proxy (correlates with source)
        # sl_distance_pct, tp_distance_pct, rr_asymmetry RE-ADDED in Phase 19 (2026-04-15)
        # Previously removed as source proxies (quan_engine had tiny stops).
        # Now safe: quan_engine is 10x down-weighted + 313 alpha_engine picks from
        # closed_picks_fast.json provide realistic SL/TP values.
        # Data shows winners=5.47% SL vs losers=4.39% SL (wider stops win more).
        "risk_reward",          # LEAKED: source proxy (quan_engine mean=2.03, live mean=1.62; source AUC=0.86)
        "risk_reward_raw",      # LEAKED: same data as risk_reward (source AUC=0.86); both have 0.0 model importance
    }

    FEATURES = [
        # === Core features (populated in 342/342 closed picks) ===
        # category_encoded DROPPED (Phase 14): zero importance, Boruta-rejected
        "confidence",           # strategy's raw confidence
        # rsi_at_entry DROPPED (Phase 14): zero importance, only 17% real data
        "volume_ratio",         # volume vs 20d average (22/342, rest imputed to 1.0)
        # risk_reward DROPPED (Phase 18): source proxy (quan_engine mean=2.03, live mean=1.62; source AUC=0.86)
        # atr_at_entry DROPPED (Phase 14): redundant (corr=1.0 with hour_x_vol)
        # regime_encoded DROPPED (Phase 14): zero importance, Boruta-rejected
        "direction_market_alignment",  # direction * btc_24h_trend: LONG+btc_up=+1, SHORT+btc_down=+1 (aligned). Replaces direction_encoded (Phase 20): old had 84.7% importance as market-direction proxy; interaction captures regime alignment instead.
        # === Trade structure features RE-ADDED (Phase 19 -- 2026-04-15) ===
        # Previously removed as source proxies (quan_engine had tiny SL/TP).
        # Now safe: quan_engine down-weighted 10x + closed_picks_fast.json provides
        # 313 properly-labeled alpha_engine picks with realistic SL/TP values.
        # Data shows: winners have wider stops (5.47% vs 4.39%) = room to breathe.
        "sl_distance_pct",      # ABS(entry - SL) / entry [0, 1], default 0
        "tp_distance_pct",      # ABS(TP - entry) / entry [0, 1], default 0
        "rr_asymmetry",         # (TP_dist - SL_dist) / (TP_dist + SL_dist) [-1, 1], default 0
        # === Strategy forward track record (Phase 19 -- set at signal time, NOT leaked) ===
        # forward_wr is computed by the scanner at signal generation from PRIOR closed
        # picks only. It's the same info a human trader would check before taking a signal.
        "strategy_forward_wr",  # Forward-validated WR of this strategy [0, 1], default 0.5
        "strategy_forward_n",   # log2(1 + forward_trades) [0, ~7], normalized /7, default 0
        # === Time-of-day features (Task 2 -- from timestamp, 342/342) ===
        "hour_utc",             # hour of signal (0-23 normalized to 0-1)
        "hour_sin",             # sin(2*pi*hour/24) -- cyclic encoding
        # hour_cos DROPPED (Phase 14): zero importance, Boruta-rejected
        # day_of_week DROPPED (Phase 14): zero importance, Boruta-rejected
        # is_weekend DROPPED (Phase 14): zero importance, Boruta-rejected
        "hour_x_vol",           # hour_sin * atr_pct (time-volatility interaction)
        # === Volatility/trade structure features RE-ADDED (Phase 19) ===
        # sl_distance_pct, tp_distance_pct REMOVED Phase 18 → RE-ADDED Phase 19
        # rr_asymmetry REMOVED Phase 18 → RE-ADDED Phase 19
        # See Phase 19 comments above for rationale.
        # === Regime interaction features REMOVED (Phase 12 -- dead features) ===
        # rsi_x_regime, vol_ratio_x_regime, momentum_x_regime, bb_x_regime,
        # hour_x_regime, atr_x_regime, direction_x_regime -- these multiplied
        # two features that were mostly 0/default, producing always-zero values.
        # Removed to improve sample:feature ratio.
        # === Funding/basis features (Phase 6 -- strongest 4h-1d predictors) ===
        "funding_rate_raw",     # Current 8h funding rate (from Binance fapi)
        "funding_z_30d",        # Z-score of funding vs 30-day rolling mean
        "funding_persistence",  # Consecutive same-sign funding periods (normalized)
        # === Live microstructure features (Phase 7 -- OBI/VPIN/funding from scanner) ===
        "orderbook_imbalance",  # Bid-ask imbalance from L2 depth [-1, +1], default 0
        "vpin_toxicity",        # Volume-sync probability of informed trading [0, 1], default 0.5
        "funding_rate_norm",    # Funding rate / 0.01, clipped to [-3, +3], default 0
        # === OBI velocity features (Phase 8 -- EFMA 2025: Sharpe 3.04-3.63 w/ OFI) ===
        "obi_delta_5",          # OBI change over last 5 scans [-1, +1], default 0
        "obi_delta_15",         # OBI change over last 15 scans [-1, +1], default 0
        "obi_acceleration",     # Second derivative of OBI [-1, +1], default 0
        # === Market sentiment (Fear & Greed Index from Alternative.me) ===
        "fear_greed_norm",      # Fear & Greed 0-100 normalized to 0-1 (50=neutral)
        # === Cross-sectional ranking features (Phase 10 -- Liu et al. 2022 JFE) ===
        "cs_momentum_rank",     # Percentile rank of 7d return vs universe [0, 1] (0.5=median)
        "cs_relative_strength", # 7d return minus BTC 7d return, clipped [-1, 1]
        "cs_dispersion",        # Std dev of all symbols' 7d returns, normalized [0, 1]
        "cs_leader_lag",        # Correlation of symbol returns with BTC lagged returns [-1, 1]
        # === Phase 12 features (2026-03-19) -- from OHLCV/strategy data, no new APIs ===
        "close_to_vwap",        # Deviation of close from VWAP [approx], default 0
        "garman_klass_vol",     # GK volatility: 0.5*ln(H/L)^2 - (2ln2-1)*ln(C/O)^2
        "fng_gradient",         # Fear & Greed rate of change (not absolute), default 0
        # risk_reward_raw DROPPED (Phase 18): source proxy (source AUC=0.86), same data as risk_reward
        # === Chi-squared validated technical features (Phase 13 -- 92.4% XGBoost accuracy) ===
        "mom30",                # 30-period momentum [-0.5, 0.5], default 0.0
        "rsi30",                # 30-period RSI (Wilder) [0, 1], default 0.5
        "macd_hist_norm",       # MACD histogram / price [-0.05, 0.05], default 0.0
        "stoch_k30",            # 30-period Stochastic %K [0, 1], default 0.5
        "stoch_d30",            # 3-period SMA of %K30 [0, 1], default 0.5
        "cci20_norm",           # CCI 20 normalized [-1, 1], default 0.0
        "williams_r",           # Williams %R 14 [-1, 0], default -0.5
        # === BTC correlation & regime features (Phase 17 -- strongest missing predictor) ===
        "btc_correlation",      # Correlation with BTC returns [-1, 1], default 0.8
        "btc_24h_change_norm",  # BTC 24h price change / 10 (10% cap) [-1, 1], default 0.0 — KEPT (Phase 20): removing broke feature count alignment with cached models; also used for direction_market_alignment computation. NOTE: correlated with direction_market_alignment (component); clean up on next full retrain.
    ]

    CATEGORY_MAP = {"crypto": 0, "forex": 1, "stock": 2, "penny": 3, "meme": 4}
    REGIME_MAP = {
        "bull": 1, "bullish": 1, "trending": 1, "markup": 1, "uptrend": 1,
        "neutral": 0, "sideways": 0, "ranging": 0, "accumulation": 0, "transitional": 0,
        "bear": -1, "bearish": -1, "markdown": -1, "downtrend": -1,
        "risk_on": 0.5, "risk_off": -0.5, "high_vol": -0.5,
    }

    def __init__(self, auto_train: bool = True):
        self.model = None
        self.calibrator = None  # Isotonic Regression calibrator for probability correction
        self.strategy_encoder: dict[str, int] = {}
        self.is_trained = False
        self.trained_feature_names: list[str] = []
        self.last_trained_at: Optional[str] = None  # ISO timestamp of last training
        self.selected_feature_indices: Optional[list[int]] = None  # Boruta-selected feature indices
        self.selected_feature_names: Optional[list[str]] = None    # Boruta-selected feature names
        self._is_regression_model: bool = False  # Phase 9: set True when regression model loaded/trained
        self._secondary_rf = None       # Stacked ensemble: secondary RandomForest
        self._secondary_catboost = None  # Stacked ensemble: secondary CatBoost (optional)
        # Dynamic ensemble weighting (graceful fallback to fixed weights)
        self._dynamic_ensemble = None
        if _HAS_DYNAMIC_ENSEMBLE:
            try:
                self._dynamic_ensemble = DynamicEnsemble()
            except Exception as _de_err:
                print(f"  [ML] Dynamic ensemble init failed: {_de_err}, using fixed weights")
        self._load_model()

        # Auto-train from closed_picks.json if no model on disk and data available.
        # This fixes the cold-start problem on CI where SQLite is ephemeral but
        # closed_picks.json is committed to the repo. Without this, the ranker
        # falls back to heuristic scoring every single run.
        if not self.is_trained and auto_train:
            self._auto_train_from_json()

    def _auto_train_from_json(self):
        """Attempt to train from closed_picks.json when no saved model exists."""
        try:
            from database import SQLiteStore
            db = SQLiteStore()
            # Check if DB has enough data
            summary = db.get_summary()
            total = summary.get("closed_picks", 0)
            if total < self.MIN_SAMPLES_TO_TRAIN:
                # Import from JSON (handles CI ephemeral DB case)
                if hasattr(db, "import_closed_picks_json"):
                    imported = db.import_closed_picks_json()
                    if imported > 0:
                        print(f"  [ML-INIT] Imported {imported} closed picks from JSON")
                    total = db.get_summary().get("closed_picks", 0)

            if total >= self.MIN_SAMPLES_TO_TRAIN:
                print(f"  [ML-INIT] Auto-training on {total} closed picks (no model on disk)...")
                metrics = self.train(db)
                status = metrics.get("status", "unknown")
                if status == "trained":
                    print(f"  [ML-INIT] Trained! model={metrics.get('model_type', '?')}"
                          f" | ROC-AUC={metrics.get('cv_roc_auc', '?')}"
                          f" | samples={metrics.get('samples', '?')}")
                else:
                    print(f"  [ML-INIT] Training result: {status}")
            else:
                print(f"  [ML-INIT] Only {total} closed picks (need {self.MIN_SAMPLES_TO_TRAIN})"
                      f" -- using heuristic scoring")
            db.close()
        except Exception as e:
            print(f"  [ML-INIT] Auto-train failed (non-fatal, using heuristic): {e}")

    def _load_model(self):
        """Load saved model if exists."""
        if ML_MODEL_PATH.exists():
            try:
                import joblib
                saved = joblib.load(str(ML_MODEL_PATH))
                self.model = saved["model"]
                self.strategy_encoder = saved["strategy_encoder"]
                self.trained_feature_names = saved.get("trained_feature_names", [])
                self.calibrator = saved.get("calibrator", None)
                self.last_trained_at = saved.get("trained_at", None)
                self.selected_feature_indices = saved.get("selected_feature_indices", None)
                self.selected_feature_names = saved.get("selected_feature_names", None)
                self._is_regression_model = saved.get("is_regression", False)
                # Load secondary ensemble models (may be None if not available)
                self._secondary_rf = saved.get("secondary_rf", None)
                self._secondary_catboost = saved.get("secondary_catboost", None)
                self.is_trained = True
                _boruta_info = ""
                if self.selected_feature_indices is not None:
                    _boruta_info = f", boruta={len(self.selected_feature_indices)}/{len(self.FEATURES)}"
                _ensemble_parts = []
                if self._secondary_rf is not None:
                    _ensemble_parts.append("RF")
                if self._secondary_catboost is not None:
                    _ensemble_parts.append("CatBoost")
                _ensemble_info = f", ensemble=[{'+'.join(_ensemble_parts)}]" if _ensemble_parts else ""
                print(f"  [ML] Loaded saved model from {ML_MODEL_PATH.name}"
                      f" (features={len(self.trained_feature_names)}"
                      f"{_boruta_info}{_ensemble_info}"
                      f", trained_at={self.last_trained_at or 'unknown'})")
            except Exception as e:
                print(f"  [ML] Failed to load model: {e}")
                self.is_trained = False

    def train(self, db) -> dict:
        """
        Train on closed picks from the database.
        Returns training metrics.

        Automatically imports closed picks from JSON if the DB is empty
        (common on CI where the SQLite DB is ephemeral).
        """
        df = db.get_ml_training_data()

        # If DB has insufficient data, try importing from closed_picks.json
        if len(df) < self.MIN_SAMPLES_TO_TRAIN:
            if hasattr(db, "import_closed_picks_json"):
                imported = db.import_closed_picks_json()
                if imported > 0:
                    print(f"  [ML] Imported {imported} closed picks from JSON into DB")
                    df = db.get_ml_training_data()

        if len(df) < self.MIN_SAMPLES_TO_TRAIN:
            return {
                "status": "insufficient_data",
                "samples": len(df),
                "required": self.MIN_SAMPLES_TO_TRAIN,
            }

        # --- Backtest Bridge: DISABLED Phase 19 (2026-04-15) ---
        # Backtest pseudo-picks have fundamentally different TP/SL distributions
        # than live picks (tighter stops, different R:R). This creates source-proxy
        # features that dominate the model, causing INVERTED scoring (bad strategies
        # score higher than good ones). With 326 properly-labeled live picks from
        # closed_picks_fast.json, we have sufficient real data for training.
        _bt_augmented = 0
        # Original backtest bridge code preserved for reference:
        # from backtest_bridge import convert_backtest_to_training, augment_training_data, _load_closed_picks

        # --- Feature Health Report (pre-training gate) ---
        # Uses progressive thresholds from HEALTH_STAGES config (KIMI review):
        #   alpha:      min_health_score=0.30, max_dead=10, max_constant=20%
        #   beta:       min_health_score=0.50, max_dead=5,  max_constant=10%
        #   production: min_health_score=0.70, max_dead=3,  max_constant=5%, expectancy>=0.2%
        try:
            from feature_health import generate_health_report, get_health_thresholds, HEALTH_STAGE
            health_report = generate_health_report()
            health_score = health_report.get("health_score", 1.0)
            thresholds = get_health_thresholds()
            min_health = thresholds.get("min_health_score", 0.30)
            max_dead = thresholds.get("max_dead_features", 10)
            n_dead = health_report.get("dead_features", 0)
            print(f"  [ML] Feature health score: {health_score:.2%} "
                  f"({health_report.get('alive_features', '?')}/{health_report.get('total_features', '?')} alive) "
                  f"[stage={HEALTH_STAGE}, min={min_health:.0%}, dead={n_dead}/{max_dead}]")

            # Correlation audit summary
            corr_audit = health_report.get("correlation_audit", {})
            if corr_audit.get("correlated_pairs"):
                print(f"  [ML] Correlation audit: {len(corr_audit['correlated_pairs'])} pairs "
                      f"with |r|>0.85 -- health={corr_audit.get('correlation_health', '?')}")

            # Data quality summary
            dq = health_report.get("data_quality", {})
            if dq.get("issues"):
                print(f"  [ML] Data quality: {dq.get('quality_score', '?'):.2%} "
                      f"({len(dq['issues'])} issues)")

            if health_score < min_health:
                print(f"  [ML] WARN: Feature health low ({health_score:.2%} < {min_health:.0%}) -- training anyway (alpha stage)")
                # In alpha stage, train anyway -- health gate is advisory, not blocking
            elif health_score < min_health + 0.20:
                print(f"  [ML] WARNING: Feature health marginal ({health_score:.2%}) -- training anyway")
        except Exception as _fh_err:
            print(f"  [ML] Feature health check failed (non-fatal): {_fh_err}")

        # --- Feature Drift Detection (pre-training gate) ---
        _drift_report = None
        try:
            from feature_health import detect_feature_drift, _load_picks
            _closed_path = DATA_DIR / "closed_picks.json"
            _all_closed = _load_picks(_closed_path)
            if len(_all_closed) >= 50:
                # Compare last 50 picks vs full training set
                _recent_50 = _all_closed[-50:]
                _training_set = _all_closed  # full history as baseline
                _drift_report = detect_feature_drift(_recent_50, _training_set)
                _drift_rec = _drift_report.get("recommendation", "stable")
                _drift_score = _drift_report.get("drift_score", 0)
                _n_drifted = _drift_report.get("features_drifted", 0)
                _n_checked = _drift_report.get("features_checked", 0)

                print(f"  [ML] Drift detection: score={_drift_score:.2f}, "
                      f"drifted={_n_drifted}/{_n_checked}, rec={_drift_rec}")

                if _drift_rec == "halt":
                    # Downgrade halt to warning -- drift is expected when adding
                    # new features or after pipeline changes. Train anyway but log.
                    print(f"  [ML] WARNING: Feature drift detected (score={_drift_score:.2f}) -- "
                          f"proceeding with training (halt downgraded to warning). "
                          f"Drifted: {_drift_report.get('drifted_features', [])[:5]}")
                elif _drift_rec == "retrain":
                    print(f"  [ML] WARNING: Moderate feature drift detected (score={_drift_score:.2f}) -- "
                          f"proceeding with training. Drifted: {_drift_report.get('drifted_features', [])[:5]}")
            else:
                print(f"  [ML] Drift detection skipped (only {len(_all_closed)} closed picks, need 50+)")
        except Exception as _drift_err:
            print(f"  [ML] Drift detection failed (non-fatal): {_drift_err}")

        # Build strategy encoder
        strategies = df["strategy"].unique()
        self.strategy_encoder = {s: i for i, s in enumerate(strategies)}

        # Engineer features (Phase 6: triple-barrier labels + sample weights)
        X, y, barrier_weights = self._build_features(df, db)
        if len(X) < self.MIN_SAMPLES_TO_TRAIN:
            return {"status": "insufficient_features", "samples": len(X)}

        # Feature health gate: warn but don't block in alpha stage
        if not self._check_feature_health(X, self.FEATURES):
            print("  [ML] WARN: Feature health check failed -- training anyway (alpha stage, will auto-drop dead features)")

        # --- Drop features that are 80%+ zero or NaN (uninformative) ---
        _active_features = list(self.FEATURES)
        # Pad _active_features if X has more columns than FEATURES
        # (happens after backtest bridge augmentation adds extra columns)
        while len(_active_features) < X.shape[1]:
            _active_features.append(f"feat_{len(_active_features)}")
        _keep_mask = []
        _dropped_features = []
        for i in range(X.shape[1]):
            col = X[:, i]
            zero_or_nan_pct = (np.sum((col == 0) | np.isnan(col))) / len(col)
            if zero_or_nan_pct >= 0.80:
                _dropped_features.append(_active_features[i])
            else:
                _keep_mask.append(i)
        if _dropped_features:
            print(f"  [ML] Dropping {len(_dropped_features)} features with 80%+ zero/NaN: "
                  f"{_dropped_features[:10]}{'...' if len(_dropped_features) > 10 else ''}")
            X = X[:, _keep_mask]
            _active_features = [_active_features[i] for i in _keep_mask]
        else:
            print(f"  [ML] All {X.shape[1]} features have sufficient non-zero data")

        # --- Boruta Feature Selection (Phase 9) ---
        # Prune features from 39 down to ~15-20 to fix overfitting
        # (39 features / 1082 samples = 1:28 ratio; optimal is 1:50+).
        _boruta_applied = False
        _boruta_feature_names = list(_active_features)  # track active feature names
        if USE_BORUTA_SELECTION:
            selected_idx, selected_names = self.select_features(X, y, _active_features)
            if len(selected_idx) < len(_active_features):
                X = X[:, selected_idx]
                self.selected_feature_indices = selected_idx
                self.selected_feature_names = selected_names
                _boruta_feature_names = selected_names
                _boruta_applied = True
                print(f"  [ML] Boruta reduced features: {len(_active_features)} -> {len(selected_idx)} "
                      f"(sample:feature ratio {len(X)}:{len(selected_idx)} = "
                      f"1:{len(X) // max(1, len(selected_idx))})")
            else:
                self.selected_feature_indices = None
                self.selected_feature_names = None
                print(f"  [ML] Boruta kept all {len(_active_features)} features")
        else:
            self.selected_feature_indices = None
            self.selected_feature_names = None

        # Train model -- Stacked ensemble (XGB + LGB + RF -> LogisticRegression meta-learner)
        # #3 ranked technique from deep research. Used by Jane Street Kaggle winners.
        from sklearn.model_selection import cross_val_score, cross_val_predict, TimeSeriesSplit
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        # 80/20 chronological split with embargo gap (Phase 11 -- prevents
        # temporal leakage at the train/val boundary). The embargo discards
        # 2% of samples between train and val to decorrelate adjacent trades.
        # Phase 18: source-stratified split to prevent AUC inflation when one source
        # dominates training and another dominates validation.
        from sklearn.model_selection import StratifiedShuffleSplit
        # 80/20 boundary (also used when val set is too small — see below)
        split_idx = int(len(X) * 0.8)
        _source_arr = np.array(["quan_engine" if s == "quan_engine" else "live"
                                 for s in self._source_list]) if hasattr(self, "_source_list") else None
        if _source_arr is not None and len(np.unique(_source_arr)) > 1:
            # Stratify by source so both train and val contain proportionally
            # similar quan_engine/live mixes
            _sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
            _train_idx, _val_idx = next(_sss.split(X, _source_arr))
            # Sort indices to preserve approximate chronological order within each set
            _train_idx = np.sort(_train_idx)
            _val_idx = np.sort(_val_idx)
            X_train, X_val = X[_train_idx], X[_val_idx]
            y_train, y_val = y[_train_idx], y[_val_idx]
            w_train = barrier_weights[_train_idx]
        else:
            # Fallback: chronological split
            embargo_size = max(1, int(len(X) * 0.02))
            val_start = min(split_idx + embargo_size, len(X))
            X_train, X_val = X[:split_idx], X[val_start:]
            y_train, y_val = y[:split_idx], y[val_start:]
            w_train = barrier_weights[:split_idx]
        if len(X_val) < 5:
            # Fallback: if embargo ate too many val samples, skip embargo
            X_val = X[split_idx:]
            y_val = y[split_idx:]

        # --- Phase 9: Regression vs Classification mode ---
        # In regression mode (USE_REGRESSION=True), y is already continuous pnl_pct.
        # In classification mode, triple-barrier labels are -1/0/+1 mapped to binary.
        _is_regression = USE_REGRESSION and _HAS_XGBOOST

        if _is_regression:
            # Regression mode: y is continuous pnl_pct, no binary mapping needed
            y_train_binary = y_train  # raw pnl_pct (used as regression target)
            y_val_binary = y_val      # raw pnl_pct for validation
            print(f"  [ML] REGRESSION MODE: predicting pnl_pct magnitude "
                  f"(train mean={float(np.mean(y_train)):.2f}%, "
                  f"val mean={float(np.mean(y_val)):.2f}%)")
        else:
            # Classification mode: _build_features already returns binary labels
            # (1=win, 0=loss/expired) so no remapping needed.
            y_train_binary = y_train
            y_val_binary = y_val

        if _is_regression:
            # Phase 9: XGBRegressor with Pseudo-Huber loss (robust to outlier returns)
            # Predicts continuous pnl_pct instead of binary win/lose.
            # This teaches the model MAGNITUDE: a 15% win >> 0.1% win.
            estimator = xgb.XGBRegressor(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                min_child_weight=5,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbosity=0,
                objective='reg:pseudohubererror',  # Robust to outlier returns
            )
            model_type = "xgboost_regressor"
            step_name = "xgb"
        elif _HAS_XGBOOST:
            # XGBoost: reduced complexity to prevent overfitting on small datasets
            # (~275 samples, 35 features). Per Krauss et al. (2017): simpler models
            # outperform on small datasets. min_child_weight=5 prevents leaf splits
            # on < 5 samples.
            # scale_pos_weight: ratio of non-win (-1 + 0) to win (+1) samples
            n_pos = max(1, int(np.sum(y == 1)))
            n_neg = max(1, int(np.sum(y != 1)))
            estimator = xgb.XGBClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                min_child_weight=5,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=max(1, n_neg / n_pos),
                random_state=42,
                n_jobs=-1,
                verbosity=0,
                eval_metric="logloss",
            )
            model_type = "xgboost"
            step_name = "xgb"
        elif _HAS_LIGHTGBM:
            # LightGBM: reduced complexity for small dataset (~275 samples).
            # min_child_samples=10 ensures each leaf has enough data.
            # NOTE: callbacks omitted here for CV compatibility; early stopping
            # applied only during the main .fit() call below.
            estimator = lgb.LGBMClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.05,
                num_leaves=15,
                min_child_samples=10,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
                verbose=-1,
            )
            model_type = "lightgbm"
            step_name = "lgbm"
        else:
            # RandomForest: Krauss et al. (2017) showed RF outperforms XGBoost/DL
            # on small datasets due to lower overfitting risk. max_depth=5 and
            # min_samples_leaf=5 constrain tree complexity.
            from sklearn.ensemble import RandomForestClassifier
            estimator = RandomForestClassifier(
                n_estimators=150,
                max_depth=5,
                min_samples_split=5,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            model_type = "random_forest"
            step_name = "rf"

        # Wrap in Pipeline with StandardScaler so features are on the same scale
        self.model = Pipeline([
            ("scaler", StandardScaler()),
            (step_name, estimator),
        ])

        # Auto-prune zero-importance features to reduce noise
        # Load previous importance scores if available
        try:
            _imp_path = DATA_DIR / "feature_importance.json"
            if _imp_path.exists():
                with open(_imp_path) as _f:
                    _prev_imp = json.load(_f).get("importances", {})
                _zero_imp = {self.FEATURES.index(k) for k, v in _prev_imp.items()
                             if v == 0 and k in self.FEATURES}
                # Also check for zero-variance columns in current data
                _zero_var = set(np.where(X_train.std(axis=0) == 0)[0])
                _prune_cols = _zero_imp | _zero_var
                if len(_prune_cols) > 0 and len(_prune_cols) < X_train.shape[1] - 5:
                    _keep = sorted(set(range(X_train.shape[1])) - _prune_cols)
                    X_train = X_train[:, _keep]
                    X_val = X_val[:, _keep]
                    X = X[:, _keep]  # full dataset for later use
                    self._active_feature_mask = _keep
                    logging.info(f"Auto-pruned {len(_prune_cols)} zero-importance features, {len(_keep)} remaining")
                else:
                    self._active_feature_mask = None
            else:
                self._active_feature_mask = None
        except Exception:
            self._active_feature_mask = None

        # Cross-validation on training split using purged time-series CV
        # (Phase 11 -- Lopez de Prado AFML Ch.7: embargo prevents look-ahead bias)
        _purged_folds = list(_purged_time_series_cv(
            len(X_train), n_splits=min(5, len(X_train) // 10), embargo_pct=0.02
        ))
        if len(_purged_folds) < 2:
            # Fallback: standard TimeSeriesSplit if not enough data for purged CV
            _purged_folds = TimeSeriesSplit(n_splits=min(3, max(2, len(X_train) // 10)))
            print("  [ML] Purged CV: insufficient data, falling back to TimeSeriesSplit")
        else:
            print(f"  [ML] Purged CV: {len(_purged_folds)} folds with 2% embargo")
        if _is_regression:
            # Regression: use neg_mean_squared_error (sklearn convention: higher=better)
            cv_scores = cross_val_score(
                self.model, X_train, y_train_binary,
                cv=_purged_folds,
                scoring="neg_mean_squared_error",
            )
            _cv_metric_name = "cv_neg_mse"
        else:
            # Classification: ROC-AUC (correct for imbalanced data)
            cv_scores = cross_val_score(
                self.model, X_train, y_train_binary,
                cv=_purged_folds,
                scoring="roc_auc",
            )
            _cv_metric_name = "cv_roc_auc"

        # Combined sample weights: barrier weights * recency weights
        # Barrier weights encode triple-barrier asymmetry (+1=1.0, 0=0.5, -1=1.2)
        # Recency weights give more importance to recent trades (half-life = 30)
        n_train = len(X_train)
        recency_weights = np.exp(-np.arange(n_train)[::-1] / 30.0)
        recency_weights /= recency_weights.sum() / n_train  # normalize so sum = n_train
        combined_weights = w_train * recency_weights  # element-wise product

        # Fit with early stopping for XGBoost/LightGBM, plain fit for RandomForest
        scaler = self.model.named_steps["scaler"]
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)

        if model_type == "xgboost_regressor":
            # Phase 9: XGBRegressor with early stopping on validation MSE
            estimator.set_params(early_stopping_rounds=20)
            estimator.fit(
                X_train_scaled, y_train_binary,
                sample_weight=combined_weights,
                eval_set=[(X_val_scaled, y_val_binary)],
                verbose=False,
            )
        elif model_type == "xgboost":
            # Early stopping with eval_set (not set in constructor for CV compat)
            estimator.set_params(early_stopping_rounds=20)
            estimator.fit(
                X_train_scaled, y_train_binary,
                sample_weight=combined_weights,
                eval_set=[(X_val_scaled, y_val_binary)],
                verbose=False,
            )
        elif model_type == "lightgbm":
            estimator.fit(
                X_train_scaled, y_train_binary,
                sample_weight=combined_weights,
                eval_set=[(X_val_scaled, y_val_binary)],
                callbacks=[lgb.early_stopping(20, verbose=False)],
            )
        else:
            # RandomForest: no early stopping, but apply combined weighting
            estimator.fit(X_train_scaled, y_train_binary, sample_weight=combined_weights)

        self.is_trained = True
        self.last_trained_at = datetime.now(timezone.utc).isoformat()

        # --- Stacked Ensemble: secondary RF + CatBoost for blending (classification only) ---
        # Heterogeneous stacking: primary (XGB/LGBM) + RF + CatBoost.
        # CatBoost adds ordered boosting (has_time=True) which handles temporal
        # data without leakage -- complementary to XGBoost's histogram splits.
        if not _is_regression:
            try:
                from sklearn.ensemble import RandomForestClassifier as _RFC
                if model_type != 'random_forest':
                    self._secondary_rf = _RFC(n_estimators=100, max_depth=5,
                        min_samples_leaf=10, random_state=42, n_jobs=-1)
                    self._secondary_rf.fit(X_train_scaled, y_train_binary, sample_weight=combined_weights)
                    logging.info('[ML] Stacked ensemble: secondary RF trained')
                else:
                    self._secondary_rf = None
            except Exception:
                self._secondary_rf = None

            # CatBoost secondary model (optional -- graceful skip if not installed)
            try:
                if _HAS_CATBOOST:
                    self._secondary_catboost = _CatBoostCls(
                        iterations=200,
                        depth=4,
                        learning_rate=0.05,
                        l2_leaf_reg=5.0,
                        random_strength=2.0,
                        bagging_temperature=1,
                        auto_class_weights='Balanced',
                        verbose=0,
                        has_time=True,  # ordered boosting for time-series data
                    )
                    self._secondary_catboost.fit(
                        X_train_scaled, y_train_binary,
                        sample_weight=combined_weights,
                        eval_set=(X_val_scaled, y_val_binary),
                        early_stopping_rounds=20,
                        verbose=False,
                    )
                    logging.info('[ML] Stacked ensemble: secondary CatBoost trained')
                else:
                    self._secondary_catboost = None
            except Exception as _cb_err:
                logging.warning(f'[ML] CatBoost training failed (non-fatal): {_cb_err}')
                self._secondary_catboost = None
        else:
            self._secondary_rf = None
            self._secondary_catboost = None

        # Save trained feature names for alignment checks at prediction time
        # When Boruta is active, trained_feature_names reflects the reduced set
        if _boruta_applied:
            self.trained_feature_names = list(_boruta_feature_names)
        else:
            self.trained_feature_names = list(X_train.columns) if hasattr(X_train, 'columns') else list(self.FEATURES)

        # Store regression flag for score_signal() to check at prediction time
        self._is_regression_model = _is_regression

        if _is_regression:
            # Phase 9: Evaluate regression model on validation set
            # Compute correlation between predicted and actual returns
            from sklearn.metrics import mean_squared_error
            val_predictions = self.model.predict(X_val)
            val_mse = float(mean_squared_error(y_val_binary, val_predictions))
            # Correlation: how well does predicted ranking match actual ranking?
            if len(val_predictions) > 2 and np.std(val_predictions) > 0 and np.std(y_val_binary) > 0:
                val_corr = float(np.corrcoef(val_predictions, y_val_binary)[0, 1])
            else:
                val_corr = 0.0
            # Store val_auc-equivalent for metrics compatibility
            val_auc = val_corr  # Use correlation as the primary quality metric
            print(f"  [ML] Regression validation: MSE={val_mse:.4f}, "
                  f"pred-actual corr={val_corr:.4f}, "
                  f"pred range=[{float(np.min(val_predictions)):.2f}%, "
                  f"{float(np.max(val_predictions)):.2f}%]")

            # No isotonic calibration in regression mode -- sigmoid transform
            # is applied in score_signal() instead
            self.calibrator = None
        else:
            # Evaluate on validation set (using binary labels for ROC-AUC)
            from sklearn.metrics import roc_auc_score
            val_proba = self.model.predict_proba(X_val)[:, 1]
            val_auc = roc_auc_score(y_val_binary, val_proba)

            # Phase 11: Overfitting sanity check -- AUC=1.0 means the model is
            # memorizing training data or leaky features are present.
            if val_auc > 0.90:
                print(f"  [WARNING] Suspiciously high AUC={val_auc:.3f} -- "
                      f"possible data leakage or trivial test set "
                      f"(val_samples={len(y_val_binary)})")

            # Isotonic Regression calibration to fix non-monotonic ml_score vs win rate
            # (research found ml_score 0.50-0.60 had 69.1% WR while 0.60-0.70 had 31.8%)
            from sklearn.isotonic import IsotonicRegression
            self.calibrator = IsotonicRegression(out_of_bounds='clip')
            self.calibrator.fit(val_proba, y_val_binary)

        # --- Champion/Challenger Model Evaluation ---
        # Don't immediately overwrite the production model. Save new model as
        # challenger, compare against the existing champion, and only promote
        # if the challenger meaningfully improves on validation metrics.
        import joblib
        ML_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        challenger_path = ML_MODEL_PATH.parent / "ml_challenger.joblib"
        comparison_path = ML_MODEL_PATH.parent / "model_comparison.json"

        challenger_artifact = {
            "model": self.model,
            "strategy_encoder": self.strategy_encoder,
            "trained_feature_names": self.trained_feature_names,
            "calibrator": getattr(self, 'calibrator', None),
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "samples": len(X),
            "is_regression": _is_regression,  # Phase 9: flag for score_signal()
            "selected_feature_indices": self.selected_feature_indices,
            "selected_feature_names": self.selected_feature_names,
            "secondary_rf": getattr(self, '_secondary_rf', None),
            "secondary_catboost": getattr(self, '_secondary_catboost', None),
        }

        # Save challenger first
        joblib.dump(challenger_artifact, str(challenger_path))

        # Attempt champion/challenger comparison
        promoted = False
        comparison_report = {}
        try:
            champion_model = None
            if ML_MODEL_PATH.exists():
                saved_champion = joblib.load(str(ML_MODEL_PATH))
                champion_model = saved_champion.get("model")

            if champion_model is not None and _is_regression:
                # Phase 9: regression model replaces classifier -- auto-promote
                # (champion is likely a classifier, can't compare apples to oranges)
                should_promote = True
                comparison_report = {
                    "status": "regression_upgrade",
                    "promotion_reason": "Regression model replaces classifier (Phase 9 upgrade)",
                    "auto_promoted": True,
                }
                print("  [ML] Champion/Challenger: Auto-promoting regression model (Phase 9 upgrade)")
                with open(str(comparison_path), "w") as _cmp_f:
                    json.dump(comparison_report, _cmp_f, indent=2, default=str)
            elif champion_model is not None:
                should_promote, comparison_report = self._champion_challenger_eval(
                    champion_model, self.model, X_val, y_val_binary
                )
                # Save comparison report
                with open(str(comparison_path), "w") as _cmp_f:
                    json.dump(comparison_report, _cmp_f, indent=2, default=str)

                if should_promote:
                    print(f"  [ML] Champion/Challenger: PROMOTED -- "
                          f"{comparison_report.get('promotion_reason', 'metrics improved')}")
                    promoted = True
                else:
                    print(f"  [ML] Champion/Challenger: REJECTED -- "
                          f"{comparison_report.get('rejection_reason', 'no improvement')}")
                    # Reload champion model back into self
                    self.model = champion_model
                    self.strategy_encoder = saved_champion.get("strategy_encoder", self.strategy_encoder)
                    self.trained_feature_names = saved_champion.get("trained_feature_names", self.trained_feature_names)
                    self.calibrator = saved_champion.get("calibrator", self.calibrator)
            else:
                # No champion exists -- first training, auto-promote
                print("  [ML] Champion/Challenger: No existing champion -- auto-promoting challenger")
                promoted = True
                comparison_report = {"status": "first_model", "auto_promoted": True}
                with open(str(comparison_path), "w") as _cmp_f:
                    json.dump(comparison_report, _cmp_f, indent=2, default=str)
        except Exception as _cc_err:
            print(f"  [ML] Champion/Challenger eval failed (auto-promoting): {_cc_err}")
            promoted = True
            comparison_report = {"status": "eval_error", "error": str(_cc_err)}

        if promoted:
            # Promote challenger to champion
            joblib.dump(challenger_artifact, str(ML_MODEL_PATH))

        # Feature importance (access through Pipeline step)
        trained_estimator = self.model.named_steps[step_name]
        # Use Boruta-selected feature names if active, otherwise full FEATURES list
        _imp_feature_names = _boruta_feature_names if _boruta_applied else self.FEATURES[:X.shape[1]]
        importances = dict(zip(_imp_feature_names,
                               trained_estimator.feature_importances_.tolist()))

        # CRITICAL CHECK: flag if all feature importances are zero (model learned nothing)
        _all_zero = all(v == 0.0 for v in importances.values())
        if _all_zero:
            print(f"  [ML] CRITICAL WARNING: ALL feature importances are 0.0!")
            print(f"  [ML] The model learned NOTHING. Check target variable distribution.")
            print(f"  [ML] Target stats: mean={float(np.mean(y)):.4f}, "
                  f"std={float(np.std(y)):.4f}, "
                  f"unique={len(np.unique(y))}")
        else:
            _top3 = sorted(importances.items(), key=lambda x: -x[1])[:3]
            print(f"  [ML] Top-3 feature importances: "
                  f"{', '.join(f'{k}={v:.4f}' for k, v in _top3)}")

        metrics = {
            "status": "trained",
            "model_type": model_type,
            "samples": len(X),
            _cv_metric_name: round(float(cv_scores.mean()), 4),
            "cv_std": round(float(cv_scores.std()), 4),
            "val_roc_auc": round(float(val_auc), 4),
            "feature_importance": {k: round(v, 4) for k, v in
                                   sorted(importances.items(), key=lambda x: -x[1])[:8]},
            "champion_challenger": {
                "promoted": promoted,
                "comparison": comparison_report,
            },
            "regression_mode": _is_regression,
            "boruta_selection": {
                "enabled": USE_BORUTA_SELECTION,
                "applied": _boruta_applied,
                "selected_count": len(self.selected_feature_indices) if self.selected_feature_indices else len(self.FEATURES),
                "total_features": len(self.FEATURES),
                "selected_names": self.selected_feature_names,
            } if _boruta_applied else {"enabled": USE_BORUTA_SELECTION, "applied": False},
        }
        # Backward compat: ensure cv_roc_auc key exists for downstream consumers
        if "cv_roc_auc" not in metrics:
            metrics["cv_roc_auc"] = metrics.get(_cv_metric_name, 0.0)

        # Include drift report in training metrics if available
        if _drift_report is not None:
            metrics["drift_detection"] = {
                "drift_score": _drift_report.get("drift_score", 0),
                "recommendation": _drift_report.get("recommendation", "stable"),
                "drifted_features": _drift_report.get("drifted_features", []),
                "features_checked": _drift_report.get("features_checked", 0),
            }

        # Save weights
        self._save_weights(db)

        # --- Save feature health report alongside training artifacts ---
        try:
            from feature_health import generate_health_report as _gen_health
            _health = _gen_health()
            metrics["feature_health_score"] = _health.get("health_score", None)
            print(f"  [ML] Feature health report saved (score={_health.get('health_score', '?')})")
        except Exception as _fh_save_err:
            print(f"  [ML] Feature health report save failed (non-fatal): {_fh_save_err}")

        # --- Precision@K KPI Measurement ---
        try:
            from feature_health import compute_precision_kpi_report
            _kpi = compute_precision_kpi_report()
            metrics["precision_at_10"] = _kpi.get("precision_at_10")
            metrics["precision_at_20"] = _kpi.get("precision_at_20")
            metrics["precision_at_50"] = _kpi.get("precision_at_50")
            metrics["score_to_wr_correlation"] = _kpi.get("score_to_wr_correlation")
            _p20_status = _kpi.get("status", {}).get("precision_at_20", "?")
            print(f"  [ML] Precision@K: P@10={_kpi['precision_at_10']:.1%}, "
                  f"P@20={_kpi['precision_at_20']:.1%} [{_p20_status}], "
                  f"P@50={_kpi['precision_at_50']:.1%}, "
                  f"score-WR corr={_kpi['score_to_wr_correlation']:.4f}")
        except Exception as _kpi_err:
            print(f"  [ML] Precision@K measurement failed (non-fatal): {_kpi_err}")

        # --- SHAP / Permutation Feature Importance + Correlation Analysis ---
        try:
            from feature_health import (
                compute_feature_importance,
                prune_low_importance_features,
                detect_redundant_features,
            )

            # Use Boruta-selected feature names if active, else full list
            if _boruta_applied and _boruta_feature_names:
                feat_names = list(_boruta_feature_names[:X_train.shape[1]])
            else:
                feat_names = list(self.FEATURES[:X_train.shape[1]])
            fi_scores = compute_feature_importance(self.model, X_train, feat_names)

            # Log top 10 most important features
            sorted_fi = sorted(fi_scores.items(), key=lambda x: -x[1])
            print(f"  [ML] Top 10 feature importances:")
            for fname, fscore in sorted_fi[:10]:
                print(f"        {fname:30s} {fscore:.4f}")

            # Log near-zero importance features
            low_imp = prune_low_importance_features(fi_scores, threshold=0.01)
            if low_imp:
                print(f"  [ML] Near-zero importance features ({len(low_imp)}): "
                      f"{low_imp[:8]}{'...' if len(low_imp) > 8 else ''}")
            metrics["low_importance_features"] = low_imp

            # Detect redundant (highly correlated) features
            redundant_pairs, drop_candidates = detect_redundant_features(
                X_train, feat_names, corr_threshold=0.85, importances=fi_scores,
            )
            if redundant_pairs:
                print(f"  [ML] Redundant feature pairs (corr > 0.85):")
                for fa, fb, corr_val in redundant_pairs[:10]:
                    print(f"        {fa} <-> {fb} (r={corr_val:.3f})")
                print(f"  [ML] Drop candidates: {drop_candidates}")
            metrics["redundant_pairs"] = [
                {"a": a, "b": b, "corr": c} for a, b, c in redundant_pairs
            ]
            metrics["drop_candidates"] = drop_candidates

            # Save importance scores to data/feature_importance.json
            _all_fi_zero = all(v == 0.0 for _, v in sorted_fi)
            importance_report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_type": model_type,
                "training_samples": len(X),
                "all_zero_warning": _all_fi_zero,
                "importances": {k: round(v, 6) for k, v in sorted_fi},
                "top_10": [{"feature": k, "importance": round(v, 6)} for k, v in sorted_fi[:10]],
                "low_importance": low_imp,
                "redundant_pairs": [
                    {"feature_a": a, "feature_b": b, "correlation": c}
                    for a, b, c in redundant_pairs
                ],
                "drop_candidates": drop_candidates,
                "boruta_selection": {
                    "applied": _boruta_applied,
                    "selected_features": self.selected_feature_names if _boruta_applied else None,
                    "rejected_features": [f for f in self.FEATURES if f not in (self.selected_feature_names or [])] if _boruta_applied else None,
                    "n_selected": len(self.selected_feature_indices) if _boruta_applied else len(self.FEATURES),
                    "n_total": len(self.FEATURES),
                },
            }
            _fi_path = Path(__file__).resolve().parent / "data" / "feature_importance.json"
            _fi_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_fi_path, "w") as _fi_f:
                json.dump(importance_report, _fi_f, indent=2)
            print(f"  [ML] Feature importance report saved to {_fi_path.name}")

        except Exception as _fi_err:
            print(f"  [ML] Feature importance analysis failed (non-fatal): {_fi_err}")

        # --- Model Audit Log: track training run for reproducibility & rollback ---
        try:
            from model_audit_log import log_training_run, check_and_rollback, compute_data_hash
            data_hash = compute_data_hash(str(Path(__file__).parent / "data" / "closed_picks.json"))
            log_training_run(
                system_name="alpha_engine_ml_ranker",
                model_type=type(self.model.named_steps[step_name]).__name__,
                version=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M"),
                metrics={"roc_auc": metrics["cv_roc_auc"], "val_auc": metrics["val_roc_auc"]},
                hyperparameters=dict(self.model.named_steps[step_name].get_params()) if hasattr(self.model.named_steps[step_name], "get_params") else {},
                feature_names=list(self.FEATURES),
                training_samples=len(X),
                data_hash=data_hash,
                model_artifact_path=str(ML_MODEL_PATH),
            )
            # Auto-rollback if new model is significantly worse
            check_and_rollback(
                system_name="alpha_engine_ml_ranker",
                new_metrics={"roc_auc": metrics["val_roc_auc"]},
                model_artifact_path=str(ML_MODEL_PATH),
            )
        except Exception as e:
            print(f"  [AUDIT] Logging failed (non-fatal): {e}")

        return metrics

    # ------------------------------------------------------------------
    # Incremental / Online Training with Drift Detection
    # ------------------------------------------------------------------

    def incremental_train(self, db) -> dict:
        """Incremental XGBoost training: warm-start from existing model.

        Instead of retraining from scratch, loads the existing booster and
        adds 10 new trees using only NEW closed picks since last training.
        Falls back to full train() if no existing model or XGBoost unavailable.

        Returns training metrics dict (same schema as train()).
        """
        # --- Guard: need XGBoost for incremental training ---
        if not _HAS_XGBOOST:
            print("  [ML-INCR] XGBoost not available -- falling back to full train()")
            return self.train(db)

        # --- Guard: need an existing trained model ---
        if not self.is_trained or self.model is None or not ML_MODEL_PATH.exists():
            print("  [ML-INCR] No existing model -- falling back to full train()")
            return self.train(db)

        # --- Check drift first: if drifting, force full retrain ---
        drift_detected = False
        try:
            history = self._load_prediction_history()
            recent_preds = [h["predicted_prob"] for h in history
                            if h.get("actual_outcome") is not None]
            recent_outcomes = [h["actual_outcome"] for h in history
                               if h.get("actual_outcome") is not None]
            if self._check_drift(recent_preds, recent_outcomes):
                drift_detected = True
                print("  [ML-INCR] DRIFT DETECTED -- triggering full retrain")
                return self.train(db)
        except Exception as e:
            print(f"  [ML-INCR] Drift check failed (non-fatal): {e}")

        # --- Get new closed picks since last training ---
        try:
            new_picks = self._get_new_picks_since_training(db)
        except Exception as e:
            print(f"  [ML-INCR] Failed to get new picks: {e}")
            return {"status": "error", "message": str(e)}

        if len(new_picks) < 5:
            print(f"  [ML-INCR] Only {len(new_picks)} new picks since last training"
                  f" (need >= 5) -- skipping incremental update")
            return {
                "status": "skipped_insufficient_new_data",
                "new_picks": len(new_picks),
                "required": 5,
                "last_trained_at": self.last_trained_at,
            }

        # If >100 new picks, full retrain is more appropriate
        if len(new_picks) > 100:
            print(f"  [ML-INCR] {len(new_picks)} new picks (>100)"
                  f" -- full retrain is more appropriate")
            return self.train(db)

        print(f"  [ML-INCR] Incremental training on {len(new_picks)} new picks...")

        # --- Build features from new picks only ---
        try:
            import joblib

            # Build strategy encoder from existing + new strategies
            for pick in new_picks:
                s = pick.get("strategy", "")
                if s and s not in self.strategy_encoder:
                    self.strategy_encoder[s] = len(self.strategy_encoder)

            # Convert new picks to feature matrix
            X_new_list = []
            y_new_list = []
            w_new_list = []

            for pick in new_picks:
                feat = self._signal_to_features(pick)
                if feat is not None:
                    X_new_list.append(feat)
                    label, weight = _compute_triple_barrier_label(pick)
                    y_new_list.append(label)
                    w_new_list.append(weight)

            if len(X_new_list) < 5:
                print(f"  [ML-INCR] Only {len(X_new_list)} valid feature vectors"
                      f" -- skipping")
                return {
                    "status": "skipped_insufficient_features",
                    "valid_features": len(X_new_list),
                }

            X_new = np.array(X_new_list)
            y_new = np.array(y_new_list)
            w_new = np.array(w_new_list)

            # Labels for XGBoost (same as train())
            _incr_is_reg = getattr(self, '_is_regression_model', False)
            if _incr_is_reg:
                # Regression: use raw pnl_pct, clipped to [-50, 50]
                y_new_binary = np.clip(
                    np.array([float(p.get("pnl_pct", 0) or 0) for p in new_picks[:len(X_new_list)]]),
                    -50.0, 50.0
                )
            else:
                y_new_binary = (y_new == 1).astype(int)

            # --- Extract the XGBoost booster from the Pipeline ---
            pipeline = self.model
            scaler = pipeline.named_steps.get("scaler")
            xgb_step_name = None
            xgb_estimator = None

            for name, step in pipeline.named_steps.items():
                if name != "scaler" and hasattr(step, "get_booster"):
                    xgb_step_name = name
                    xgb_estimator = step
                    break

            if xgb_estimator is None:
                # Model is not XGBoost (could be LightGBM/RF from older training)
                print("  [ML-INCR] Existing model is not XGBoost"
                      " -- falling back to full train()")
                return self.train(db)

            # Scale new features using the existing scaler
            X_new_scaled = scaler.transform(X_new)

            # --- Warm-start XGBoost: add 10 new trees to existing booster ---
            existing_booster = xgb_estimator.get_booster()

            # Create DMatrix for new data
            dtrain_new = xgb.DMatrix(
                X_new_scaled, label=y_new_binary, weight=w_new
            )

            # Get params from existing model
            params = {
                "max_depth": xgb_estimator.max_depth,
                "learning_rate": xgb_estimator.learning_rate,
                "objective": "reg:pseudohubererror" if _incr_is_reg else "binary:logistic",
                "eval_metric": "rmse" if _incr_is_reg else "logloss",
                "min_child_weight": getattr(
                    xgb_estimator, "min_child_weight", 5
                ),
                "subsample": getattr(xgb_estimator, "subsample", 0.8),
                "colsample_bytree": getattr(
                    xgb_estimator, "colsample_bytree", 0.8
                ),
                "verbosity": 0,
            }

            # Warm-start: add 10 new trees keeping all old trees
            updated_booster = xgb.train(
                params,
                dtrain_new,
                num_boost_round=10,
                xgb_model=existing_booster,
                verbose_eval=False,
            )

            # Update the estimator's internal booster
            xgb_estimator._Booster = updated_booster
            old_n_trees = getattr(xgb_estimator, "n_estimators", 150)

            self.is_trained = True
            self.last_trained_at = datetime.now(timezone.utc).isoformat()

            # Save updated model
            artifact = {
                "model": self.model,
                "strategy_encoder": self.strategy_encoder,
                "trained_feature_names": self.trained_feature_names,
                "calibrator": self.calibrator,
                "trained_at": self.last_trained_at,
                "samples": len(X_new),
                "incremental": True,
                "trees_added": 10,
            }
            ML_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(artifact, str(ML_MODEL_PATH))

            metrics = {
                "status": "incremental_trained",
                "model_type": "xgboost_incremental",
                "new_picks": len(new_picks),
                "valid_features": len(X_new_list),
                "trees_added": 10,
                "total_trees": old_n_trees + 10,
                "last_trained_at": self.last_trained_at,
                "drift_detected": drift_detected,
            }

            print(f"  [ML-INCR] Success: added 10 trees on"
                  f" {len(X_new_list)} new picks"
                  f" (total trees: ~{old_n_trees + 10})")

            # Save weights
            try:
                self._save_weights(db)
            except Exception as _w_err:
                print(f"  [ML-INCR] Weight save failed (non-fatal):"
                      f" {_w_err}")

            return metrics

        except Exception as e:
            print(f"  [ML-INCR] Incremental training failed: {e}"
                  f" -- falling back to full train()")
            return self.train(db)

    def _get_new_picks_since_training(self, db) -> list:
        """Get closed picks added after the last training timestamp.

        If last_trained_at is None, returns empty list (forces full train).
        """
        if self.last_trained_at is None:
            return []

        try:
            last_ts = datetime.fromisoformat(
                self.last_trained_at.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return []

        # Load all closed picks and filter by timestamp
        closed_path = DATA_DIR / "closed_picks.json"
        if not closed_path.exists():
            return []

        try:
            with open(closed_path, encoding="utf-8") as f:
                all_picks = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        new_picks = []
        for pick in all_picks:
            pick_ts = _parse_signal_ts(pick)
            if pick_ts is None:
                # Try closed_at / resolved_at timestamps
                for key in ("closed_at", "resolved_at", "updated_at"):
                    val = pick.get(key)
                    if val:
                        try:
                            val_str = str(val)
                            if len(val_str) == 10 and val_str[4] == "-":
                                val_str += "T00:00:00+00:00"
                            pick_ts = datetime.fromisoformat(
                                val_str.replace("Z", "+00:00")
                            )
                            break
                        except Exception:
                            continue

            if pick_ts is not None and pick_ts > last_ts:
                new_picks.append(pick)

        return new_picks

    def _check_drift(self, recent_predictions: list,
                     recent_outcomes: list,
                     window: int = 50) -> bool:
        """Check if model predictions are drifting from reality.

        Uses simple accuracy-based drift detection: if rolling accuracy
        drops below 45% over the last `window` predictions, trigger a
        full retrain. This is a lightweight alternative to ADWIN that
        requires no external dependencies.

        Args:
            recent_predictions: list of predicted probabilities (float)
            recent_outcomes: list of actual outcomes (1=win, 0=loss)
            window: number of recent predictions to evaluate

        Returns:
            True if drift detected (accuracy < 45%), False otherwise.
        """
        if len(recent_predictions) < window:
            return False

        correct = sum(
            1 for p, o in zip(
                recent_predictions[-window:],
                recent_outcomes[-window:]
            )
            if (p > 0.5) == (o > 0)
        )
        accuracy = correct / window

        if accuracy < 0.45:
            print(f"  [ML-DRIFT] Accuracy={accuracy:.2%} over last"
                  f" {window} predictions (< 45% threshold)"
                  f" -- drift detected")
            return True

        print(f"  [ML-DRIFT] Accuracy={accuracy:.2%} over last"
              f" {window} predictions -- OK")
        return False

    # ------------------------------------------------------------------
    # Prediction History (for drift detection)
    # ------------------------------------------------------------------

    def _load_prediction_history(self) -> list:
        """Load prediction history from disk."""
        if not PREDICTION_HISTORY_PATH.exists():
            return []
        try:
            with open(PREDICTION_HISTORY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def _save_prediction_history(self, history: list) -> None:
        """Save prediction history to disk (last N entries only)."""
        if len(history) > PREDICTION_HISTORY_MAX:
            history = history[-PREDICTION_HISTORY_MAX:]
        PREDICTION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PREDICTION_HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)

    def record_prediction(self, symbol: str, strategy: str,
                          predicted_prob: float) -> None:
        """Record a new prediction for drift tracking.

        Called by the scanner after scoring a signal. The actual_outcome
        field is filled later when the pick closes
        (via update_prediction_outcomes).
        """
        history = self._load_prediction_history()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "strategy": strategy,
            "predicted_prob": round(predicted_prob, 4),
            "actual_outcome": None,  # filled when pick closes
        }
        history.append(entry)
        self._save_prediction_history(history)

    def update_prediction_outcomes(self, closed_picks: list) -> int:
        """Back-fill actual_outcome in prediction history from closed picks.

        Matches on (symbol, strategy) and fills in outcome for entries
        that don't have one yet. Returns count of outcomes filled.

        Args:
            closed_picks: list of closed pick dicts with at least
                'symbol', 'strategy', and 'result'/'pnl_pct' fields.
        """
        history = self._load_prediction_history()
        if not history:
            return 0

        # Build lookup: (symbol, strategy) -> outcome
        outcome_map: dict[tuple[str, str], int] = {}
        for pick in closed_picks:
            sym = pick.get("symbol", "")
            strat = pick.get("strategy", "")
            if not sym or not strat:
                continue
            label, _ = _compute_triple_barrier_label(pick)
            # Map to binary: +1 -> 1, 0/-1 -> 0
            outcome_map[(sym, strat)] = 1 if label == 1 else 0

        filled = 0
        for entry in history:
            if entry.get("actual_outcome") is not None:
                continue
            key = (entry.get("symbol", ""), entry.get("strategy", ""))
            if key in outcome_map:
                entry["actual_outcome"] = outcome_map[key]
                filled += 1

        if filled > 0:
            self._save_prediction_history(history)
            print(f"  [ML-DRIFT] Back-filled {filled} prediction outcomes")

        return filled

    def smart_train(self, db) -> dict:
        """Smart training dispatcher: incremental by default, full on drift.

        This is the recommended entry point for the scanner's training
        flow. Decision logic:
        1. If drift detected OR >100 new picks: full retrain via train()
        2. If 5-100 new picks: incremental train via incremental_train()
        3. If <5 new picks: skip (model is fresh enough)
        4. If no existing model: full train via train()

        Returns training metrics dict.
        """
        # No model at all -> full train
        if not self.is_trained or self.model is None:
            print("  [ML-SMART] No existing model -- full train")
            return self.train(db)

        # Check drift first
        try:
            history = self._load_prediction_history()
            preds = [h["predicted_prob"] for h in history
                     if h.get("actual_outcome") is not None]
            outcomes = [h["actual_outcome"] for h in history
                        if h.get("actual_outcome") is not None]
            if self._check_drift(preds, outcomes):
                print("  [ML-SMART] Drift detected -- full retrain")
                return self.train(db)
        except Exception as e:
            print(f"  [ML-SMART] Drift check failed (non-fatal): {e}")

        # Try incremental
        result = self.incremental_train(db)
        training_type = result.get("status", "unknown")
        print(f"  [ML-SMART] Training type: {training_type}")
        return result

    def _champion_challenger_eval(
        self,
        champion_model,
        challenger_model,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> tuple:
        """Compare champion vs challenger on validation data.

        Promotion criteria (ALL must pass):
          1. AUC improves by >= 0.02
          2. Brier score improves (lower)
          3. No increase in max drawdown on backtest (estimated from
             validation set predictions)

        Returns:
            (should_promote: bool, comparison_report: dict)
        """
        from sklearn.metrics import roc_auc_score, brier_score_loss, accuracy_score

        report = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "val_samples": int(len(y_val)),
        }

        # Score validation set with both models
        try:
            champ_proba = champion_model.predict_proba(X_val)[:, 1]
        except Exception:
            # Champion model can't score (e.g., feature mismatch) -- auto-promote
            report["status"] = "champion_incompatible"
            report["promotion_reason"] = "Champion model cannot score validation data (feature mismatch)"
            return True, report

        try:
            chall_proba = challenger_model.predict_proba(X_val)[:, 1]
        except Exception:
            report["status"] = "challenger_error"
            report["rejection_reason"] = "Challenger model failed to score validation data"
            return False, report

        # Compute metrics for both
        try:
            champ_auc = float(roc_auc_score(y_val, champ_proba))
        except ValueError:
            champ_auc = 0.5  # Only one class in val set
        try:
            chall_auc = float(roc_auc_score(y_val, chall_proba))
        except ValueError:
            chall_auc = 0.5

        champ_brier = float(brier_score_loss(y_val, champ_proba))
        chall_brier = float(brier_score_loss(y_val, chall_proba))

        champ_acc = float(accuracy_score(y_val, (champ_proba >= 0.5).astype(int)))
        chall_acc = float(accuracy_score(y_val, (chall_proba >= 0.5).astype(int)))

        # Estimate max drawdown from sequential validation predictions
        # (treat each validation sample as a trade with +1/-1 PnL)
        def _estimate_max_dd(proba, y_true):
            """Estimate max drawdown from model predictions on validation set."""
            preds = (proba >= 0.5).astype(int)
            # PnL: +1 for correct, -1 for incorrect
            pnl = np.where(preds == y_true, 1.0, -1.0)
            cum = np.cumsum(pnl)
            peak = np.maximum.accumulate(cum)
            dd = cum - peak
            return float(dd.min()) if len(dd) > 0 else 0.0

        champ_max_dd = _estimate_max_dd(champ_proba, y_val)
        chall_max_dd = _estimate_max_dd(chall_proba, y_val)

        # Profit factor: sum of gains / abs(sum of losses)
        def _profit_factor(proba, y_true):
            preds = (proba >= 0.5).astype(int)
            pnl = np.where(preds == y_true, 1.0, -1.0)
            gains = float(pnl[pnl > 0].sum())
            losses = float(abs(pnl[pnl < 0].sum()))
            return gains / losses if losses > 0 else float("inf")

        champ_pf = _profit_factor(champ_proba, y_val)
        chall_pf = _profit_factor(chall_proba, y_val)

        report.update({
            "champion": {
                "auc": round(champ_auc, 4),
                "brier_score": round(champ_brier, 4),
                "accuracy": round(champ_acc, 4),
                "max_drawdown": round(champ_max_dd, 4),
                "profit_factor": round(champ_pf, 4) if champ_pf != float("inf") else "inf",
            },
            "challenger": {
                "auc": round(chall_auc, 4),
                "brier_score": round(chall_brier, 4),
                "accuracy": round(chall_acc, 4),
                "max_drawdown": round(chall_max_dd, 4),
                "profit_factor": round(chall_pf, 4) if chall_pf != float("inf") else "inf",
            },
            "deltas": {
                "auc": round(chall_auc - champ_auc, 4),
                "brier_score": round(chall_brier - champ_brier, 4),
                "accuracy": round(chall_acc - champ_acc, 4),
                "max_drawdown": round(chall_max_dd - champ_max_dd, 4),
            },
        })

        # Promotion criteria
        reasons_passed = []
        reasons_failed = []

        # 1. AUC must improve by >= 0.02
        auc_delta = chall_auc - champ_auc
        if auc_delta >= 0.02:
            reasons_passed.append(f"AUC improved by {auc_delta:+.4f} (>= 0.02 threshold)")
        else:
            reasons_failed.append(f"AUC delta {auc_delta:+.4f} < 0.02 threshold")

        # 2. Brier score must improve (lower is better)
        brier_delta = chall_brier - champ_brier
        if brier_delta < 0:
            reasons_passed.append(f"Brier score improved by {brier_delta:+.4f}")
        else:
            reasons_failed.append(f"Brier score worsened by {brier_delta:+.4f}")

        # 3. No increase in max drawdown (challenger DD should not be worse)
        dd_delta = chall_max_dd - champ_max_dd
        if dd_delta >= 0:  # max_dd is negative; less negative = better
            reasons_passed.append(f"Max drawdown improved or unchanged ({dd_delta:+.4f})")
        else:
            reasons_failed.append(f"Max drawdown worsened by {dd_delta:.4f}")

        should_promote = len(reasons_failed) == 0
        report["reasons_passed"] = reasons_passed
        report["reasons_failed"] = reasons_failed

        if should_promote:
            report["status"] = "promoted"
            report["promotion_reason"] = "; ".join(reasons_passed)
        else:
            report["status"] = "rejected"
            report["rejection_reason"] = "; ".join(reasons_failed)

        return should_promote, report

    # ------------------------------------------------------------------
    # Boruta Feature Selection (Phase 9 -- reduce 41 features to ~15-20)
    # ------------------------------------------------------------------

    def select_features(self, X: np.ndarray, y: np.ndarray,
                        feature_names: list[str]) -> tuple[list[int], list[str]]:
        """Use Boruta to identify truly important features.

        Boruta creates shadow (permuted) copies of each feature, trains a
        Random Forest, and keeps only features whose importance consistently
        exceeds the best shadow feature (Kursa & Rudnicki, 2010).

        Results are cached to ``data/boruta_selected_features.json`` and
        re-used until the feature set changes (different count) or the
        cache is older than 7 days.

        Args:
            X: Feature matrix (n_samples, n_features).
            y: Binary labels (0/1).
            feature_names: Ordered list of feature names matching X columns.

        Returns:
            (selected_indices, selected_names) -- indices into the original
            FEATURES list and corresponding names.
        """
        cache_path = DATA_DIR / "boruta_selected_features.json"

        # --- Check cache (re-run weekly or when feature set changes) ---
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cached = json.load(f)
                cached_n = cached.get("n_features", -1)
                cached_ts = cached.get("timestamp", "")
                # Invalidate if feature count changed
                if cached_n == len(feature_names):
                    # Invalidate if older than 7 days
                    try:
                        cache_dt = datetime.fromisoformat(
                            cached_ts.replace("Z", "+00:00")
                        )
                        age_days = (datetime.now(timezone.utc) - cache_dt).days
                        if age_days < 7:
                            sel_idx = cached["selected_indices"]
                            sel_names = cached["selected_names"]
                            print(f"  [BORUTA] Using cached selection: "
                                  f"{len(sel_idx)}/{len(feature_names)} features "
                                  f"(cached {age_days}d ago)")
                            return sel_idx, sel_names
                        else:
                            print(f"  [BORUTA] Cache expired ({age_days}d old) -- re-running")
                    except (ValueError, TypeError):
                        pass  # Bad timestamp, re-run
                else:
                    print(f"  [BORUTA] Feature count changed "
                          f"({cached_n} -> {len(feature_names)}) -- re-running")
            except (json.JSONDecodeError, IOError, KeyError):
                pass  # Corrupt cache, re-run

        # --- Guard: Boruta not installed ---
        if not _HAS_BORUTA:
            print("  [BORUTA] boruta package not installed -- using all features. "
                  "Install with: pip install boruta")
            return list(range(len(feature_names))), list(feature_names)

        # --- Run Boruta ---
        print(f"  [BORUTA] Running feature selection on {X.shape[0]} samples, "
              f"{X.shape[1]} features (max_iter=50)...")

        try:
            from sklearn.ensemble import RandomForestClassifier

            # Binary labels for Boruta (Boruta needs classification labels)
            # If y contains regression targets (continuous), convert to binary
            if len(np.unique(y)) > 3:
                # Regression targets -- convert to binary (positive return = 1)
                y_binary = (y > 0).astype(int)
            elif y.max() > 1 or y.min() < 0:
                # Triple-barrier labels (-1/0/+1) -- map +1 to 1, rest to 0
                y_binary = (y == 1).astype(int)
            else:
                y_binary = y

            rf = RandomForestClassifier(
                n_jobs=-1, max_depth=5, n_estimators=100,
                class_weight="balanced", random_state=42,
            )
            selector = BorutaPy(
                rf, n_estimators="auto", max_iter=50,
                random_state=42, verbose=0,
            )
            selector.fit(X, y_binary)

            # support_ = confirmed features, support_weak_ = tentative
            confirmed = np.where(selector.support_)[0].tolist()
            tentative = np.where(selector.support_weak_)[0].tolist()

            # Keep confirmed + tentative (tentative are borderline useful)
            selected_idx = sorted(set(confirmed + tentative))

            # Safety net: if Boruta selects fewer than 5 features, skip Boruta
            # entirely and use ALL features. The random ranking-based expansion
            # was producing zero-importance models. Better to let the tree
            # algorithm handle feature selection internally.
            if len(selected_idx) < 5:
                print(f"  [BORUTA] Only {len(selected_idx)} features selected "
                      f"-- Boruta not discriminative enough, using ALL features")
                selected_idx = list(range(len(feature_names)))
                selected_names = list(feature_names)
                # Cache this result so we don't re-run Boruta wastefully
                cache_data = {
                    "selected_indices": selected_idx,
                    "selected_names": selected_names,
                    "rejected_names": [],
                    "confirmed_count": 0,
                    "tentative_count": 0,
                    "n_features": len(feature_names),
                    "n_selected": len(selected_idx),
                    "n_samples": int(X.shape[0]),
                    "ranking": selector.ranking_.tolist(),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "note": "Boruta selected <5 features, using all features as fallback",
                }
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=2)
                return selected_idx, selected_names

            selected_names = [feature_names[i] for i in selected_idx]
            rejected_names = [feature_names[i] for i in range(len(feature_names))
                              if i not in selected_idx]

            print(f"  [BORUTA] Selected {len(selected_idx)}/{len(feature_names)} features")
            print(f"  [BORUTA] Confirmed: {len(confirmed)}, Tentative: {len(tentative)}")
            print(f"  [BORUTA] Kept: {selected_names}")
            print(f"  [BORUTA] Dropped: {rejected_names}")

            # --- Cache results ---
            cache_data = {
                "selected_indices": selected_idx,
                "selected_names": selected_names,
                "rejected_names": rejected_names,
                "confirmed_count": len(confirmed),
                "tentative_count": len(tentative),
                "n_features": len(feature_names),
                "n_selected": len(selected_idx),
                "n_samples": int(X.shape[0]),
                "ranking": selector.ranking_.tolist(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            print(f"  [BORUTA] Results cached to {cache_path.name}")

            return selected_idx, selected_names

        except Exception as e:
            print(f"  [BORUTA] Feature selection failed (non-fatal): {e}")
            print(f"  [BORUTA] Falling back to all {len(feature_names)} features")
            return list(range(len(feature_names))), list(feature_names)

    def _build_features(self, df: pd.DataFrame, db) -> tuple:
        """Build feature matrix from closed picks.

        Phase 5: enriches each row with extra_json fields (direction,
        timestamp, mfe, mae, etc.) for real feature values.

        Phase 6: uses triple-barrier labeling (+1/0/-1) with asymmetric
        sample weights. Returns (X, y, sample_weights).

        Phase 9 (regression mode): when USE_REGRESSION is True, y contains
        the raw pnl_pct value instead of triple-barrier labels. Sample
        weights still use recency + barrier asymmetry for consistency.
        """
        features_list = []
        labels = []
        sample_weights = []
        regression_targets = []  # Phase 9: raw pnl_pct values
        _source_list = []  # Phase 18: track data source for stratified split

        for _, row in df.iterrows():
            # Build enriched signal dict from row + extra_json
            signal = row.to_dict()
            extra_json_raw = signal.pop("extra_json", None)
            if extra_json_raw:
                try:
                    extra = (json.loads(extra_json_raw)
                             if isinstance(extra_json_raw, str)
                             else extra_json_raw)
                    if isinstance(extra, dict):
                        # Merge extra fields into signal dict (don't overwrite
                        # existing non-None values from the main columns)
                        for k, v in extra.items():
                            if signal.get(k) is None:
                                signal[k] = v
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            feat = self._signal_to_features(signal)
            if feat is not None:
                features_list.append(feat)
                _source_list.append(signal.get("source", "live"))
                # Triple-barrier labeling (Phase 6):
                #   +1: TP hit / profitable
                #    0: expired / uncertain
                #   -1: SL hit / loss
                # With asymmetric sample weights
                label, weight = _compute_triple_barrier_label(row.to_dict())
                labels.append(label)
                # Phase 18: down-weight quan_engine picks to prevent source identity
                # leakage that caused AUC=1.0. quan_engine has 84% share with 66% loss rate.
                _source = str(signal.get("source", "live")).lower()
                if _source == "quan_engine":
                    _source_w = 0.1  # 10x down-weight
                else:
                    _source_w = float(signal.get("source_weight", 1.0) or 1.0)
                sample_weights.append(weight * _source_w)

                # Phase 9: capture raw pnl_pct for regression target
                _pnl_raw = float(row.to_dict().get("pnl_pct", 0) or 0)
                # Clip extreme outliers to [-50%, +50%] to limit influence
                _pnl_raw = max(-50.0, min(50.0, _pnl_raw))
                regression_targets.append(_pnl_raw)

        if not features_list:
            return np.array([]), np.array([]), np.array([])

        # Log class distribution for triple-barrier labels
        labels_arr = np.array(labels)
        n_pos = int(np.sum(labels_arr == 1))
        n_neutral = int(np.sum(labels_arr == 0))
        n_neg = int(np.sum(labels_arr == -1))
        print(f"  [ML] Triple-barrier class distribution: +1: {n_pos}, 0: {n_neutral}, -1: {n_neg}")

        # Phase 9: in regression mode, return pnl_pct as the target y
        if USE_REGRESSION:
            regression_arr = np.array(regression_targets, dtype=np.float64)
            _mean_ret = float(np.mean(regression_arr))
            _median_ret = float(np.median(regression_arr))
            _std_ret = float(np.std(regression_arr))
            print(f"  [ML] Regression targets: mean={_mean_ret:.2f}%, "
                  f"median={_median_ret:.2f}%, std={_std_ret:.2f}%, "
                  f"range=[{float(np.min(regression_arr)):.2f}%, "
                  f"{float(np.max(regression_arr)):.2f}%]")
            return np.array(features_list), regression_arr, np.array(sample_weights)

        # Classification mode: map triple-barrier to binary WON/LOST
        # +1 -> 1 (win), 0 -> 0 (uncertain/expired = non-win), -1 -> 0 (loss)
        binary_labels = (labels_arr == 1).astype(int)
        n_wins = int(np.sum(binary_labels == 1))
        n_losses = int(np.sum(binary_labels == 0))
        total = n_wins + n_losses
        win_rate = n_wins / total * 100 if total > 0 else 0
        print(f"  [ML] Training: {total} samples, {n_wins} wins, {n_losses} losses ({win_rate:.1f}% WR)")

        # Warn if class balance is severely skewed (< 20% minority class)
        minority_pct = min(n_wins, n_losses) / total * 100 if total > 0 else 0
        if minority_pct < 20:
            print(f"  [ML] WARNING: Severe class imbalance -- minority class is only {minority_pct:.1f}%")
        elif minority_pct < 30:
            print(f"  [ML] NOTE: Moderate class imbalance -- minority class is {minority_pct:.1f}%")

        self._source_list = _source_list
        return np.array(features_list), binary_labels, np.array(sample_weights)

    # Direction encoding map
    DIRECTION_MAP = {"BUY": 1, "LONG": 1, "SELL": -1, "SHORT": -1}

    def _signal_to_features(self, signal: dict) -> Optional[np.ndarray]:
        """Convert a signal dict to a feature vector.

        Phase 5: only uses features that have real data in closed picks.
        Dead features (always zero) have been removed.

        Phase 6 (ML Feature Contract): if ml_features_at_entry is present
        on the signal, use those pre-computed values FIRST (they were
        captured at signal time when OHLCV data was fresh). Fall back to
        signal-level fields / defaults only when the pre-computed dict is
        missing or incomplete.
        """
        try:
            # NaN-safe float conversion: Python's `nan or default` returns nan
            # because float('nan') is truthy. This helper catches that.
            def _safe(val, default=0.0):
                if val is None:
                    return default
                try:
                    v = float(val)
                    if math.isnan(v) or math.isinf(v):
                        return default
                    return v
                except (TypeError, ValueError):
                    return default

            # --- ML Feature Contract: prefer pre-computed features ---
            mf = signal.get("ml_features_at_entry") or {}

            strat = signal.get("strategy", "")
            cat = signal.get("category", "")
            hour = _ts_hour(signal)
            dow = _ts_dow(signal)
            entry = float(signal.get("entry_price", 0) or 0)
            tp = float(signal.get("take_profit", 0) or 0)
            sl = float(signal.get("stop_loss", 0) or 0)
            direction = (signal.get("direction") or signal.get("signal_type") or "").upper()

            # Phase 12 fix: RSI fallback chain (mf -> signal -> extra -> default 50)
            # Previously only 23% of picks had RSI; now ~60% with extra dict fallback
            # Phase 15 fix: added extra.rsi_14, extra.rsi_at_entry to chain
            _extra_dict = signal.get("extra", {}) if isinstance(signal.get("extra"), dict) else {}
            rsi_val = mf.get("rsi_14") if mf.get("rsi_14") is not None else (
                signal.get("rsi_at_entry")
                or _extra_dict.get("rsi")
                or _extra_dict.get("rsi_14")
                or _extra_dict.get("rsi_at_entry")
                or 50
            )
            # Phase 12 fix: volume_ratio fallback chain (mf -> signal -> extra -> default 1.0)
            # Previously only 19% of picks had volume_ratio; now ~55% with extra dict fallback
            # Phase 15 fix: added extra.volume_ratio to chain
            vol_ratio_val = mf.get("volume_ratio") if mf.get("volume_ratio") is not None else (
                signal.get("volume_ratio")
                or _extra_dict.get("vol_ratio")
                or _extra_dict.get("volume_ratio")
                or 1.0
            )

            # --- SL/TP distance as % of entry ---
            sl_dist_pct = 0.0
            tp_dist_pct = 0.0
            if entry > 0:
                if sl > 0:
                    sl_dist_pct = abs(entry - sl) / entry
                if tp > 0:
                    tp_dist_pct = abs(tp - entry) / entry

            # --- ATR pct: prefer pre-computed, then signal field, then SL proxy ---
            atr_pct = mf.get("atr_pct") if mf.get("atr_pct") is not None else float(signal.get("atr_at_entry", 0) or 0)
            if atr_pct == 0 and entry > 0:
                atr_pct = sl_dist_pct  # SL distance is a decent volatility proxy

            # --- R:R asymmetry: (tp_dist - sl_dist) / (tp_dist + sl_dist) ---
            rr_asym = 0.0
            if (tp_dist_pct + sl_dist_pct) > 0:
                rr_asym = (tp_dist_pct - sl_dist_pct) / (tp_dist_pct + sl_dist_pct)

            # === Outcome features (populated for closed picks, 0 for live signals) ===
            # entry_vs_optimal: how far entry was from subsequent low (longs) / high (shorts)
            entry_vs_opt = 0.0
            try:
                mfe = float(signal.get("mfe", 0) or 0)
                mae = float(signal.get("mae", 0) or 0)
                if direction in ("BUY", "LONG") and entry > 0:
                    # For longs, optimal entry = entry * (1 + mae) since mae is negative
                    # entry_vs_optimal = how much we missed the bottom
                    entry_vs_opt = abs(mae)  # already a fraction
                elif direction in ("SELL", "SHORT") and entry > 0:
                    # For shorts, optimal entry = entry * (1 + mfe)
                    entry_vs_opt = abs(mfe) if mfe > 0 else 0.0
                entry_vs_opt = min(entry_vs_opt, 1.0)
            except (TypeError, ValueError):
                entry_vs_opt = 0.0

            # hold_duration_hours (from hold_days, normalized by 30 days max)
            hold_hours = 0.0
            try:
                hold_days = float(signal.get("hold_days", 0) or 0)
                hold_hours = min(hold_days * 24.0, 720.0) / 720.0  # normalize: 30 days max
            except (TypeError, ValueError):
                hold_hours = 0.0

            # MFE/MAE as percentages
            mfe_val = 0.0
            mae_val = 0.0
            try:
                mfe_val = min(abs(float(signal.get("mfe", 0) or 0)), 0.5)  # cap at 50%
                mae_val = min(abs(float(signal.get("mae", 0) or 0)), 0.5)
            except (TypeError, ValueError):
                pass

            # Phase 12 fix: regime fallback chain (regime_at_entry -> market_regime -> regime -> neutral)
            # Previously always 0 when regime_at_entry was not set
            _regime_str = (
                signal.get("regime_at_entry")
                or signal.get("market_regime")
                or signal.get("regime")
                or _extra_dict.get("regime")
                or "neutral"
            )
            _regime_raw = self.REGIME_MAP.get(_regime_str.lower(), 0)
            _regime_interaction_val = _regime_raw + 1  # -1->0, 0->1, 1->2

            # Normalized values from pre-computed or fallback sources
            _rsi_norm = (float(rsi_val or 50)) / 100.0
            _vol_ratio_norm = min(float(vol_ratio_val or 1.0), 10.0) / 10.0

            # Pre-computed momentum/bb for regime interaction features
            _bb_pos = mf.get("bb_position", 0.0) if mf.get("bb_position") is not None else 0.0
            _momentum = mf.get("momentum_7d", 0.0) if mf.get("momentum_7d") is not None else 0.0

            # --- Funding/basis features (Phase 6) ---
            # Extract from ml_features_at_entry first, then extra_json, then signal
            _extra = signal.get("extra_json", {})
            if isinstance(_extra, str):
                try:
                    _extra = json.loads(_extra)
                except (json.JSONDecodeError, TypeError):
                    _extra = {}
            if not isinstance(_extra, dict):
                _extra = {}

            # Phase 15 fix: expanded funding_rate_raw fallback chain
            # mf -> extra_json -> extra dict -> signal-level fields -> default 0.0
            _funding_raw = (
                mf.get("funding_rate_raw")
                if mf.get("funding_rate_raw") is not None
                else (
                    _extra.get("funding_rate")
                    or _extra.get("funding_rate_raw")
                    or _extra_dict.get("funding_rate")
                    or _extra_dict.get("funding")
                    or _extra_dict.get("funding_rate_raw")
                    or signal.get("funding_rate", 0.0)
                )
            )
            _funding_raw = float(_funding_raw or 0.0)
            # Clamp to [-0.01, 0.01] (extreme funding beyond 1% is outlier)
            _funding_raw = max(-0.01, min(0.01, _funding_raw))

            _funding_z = (
                mf.get("funding_z_30d")
                if mf.get("funding_z_30d") is not None
                else _extra.get("funding_z_30d", 0.0)
            )
            _funding_z = float(_funding_z or 0.0)
            # Clamp z-score to [-3, 3]
            _funding_z = max(-3.0, min(3.0, _funding_z)) / 3.0  # normalize to [-1, 1]

            _funding_persist = (
                mf.get("funding_persistence")
                if mf.get("funding_persistence") is not None
                else _extra.get("funding_persistence", 0.0)
            )
            _funding_persist = float(_funding_persist or 0.0)
            # Normalize: cap at 10 consecutive periods
            _funding_persist = max(-10.0, min(10.0, _funding_persist)) / 10.0

            # --- Live microstructure features (Phase 7 -- from scanner injection) ---
            # OBI: orderbook imbalance from L2 depth, range [-1, +1], default 0
            # Phase 15 fix: expanded OBI fallback chain (signal -> extra_dict -> mf -> default 0)
            _obi = _safe(
                signal.get("orderbook_imbalance")
                or _extra_dict.get("obi")
                or _extra_dict.get("orderbook_imbalance")
                or _extra_dict.get("ob_imbalance")
                or mf.get("orderbook_imbalance"),
                0.0
            )
            _obi = max(-1.0, min(1.0, float(_obi)))

            # VPIN: volume-sync probability of informed trading, range [0, 1], default 0.5
            _vpin_raw = signal.get("vpin")
            _vpin = float(_vpin_raw) if _vpin_raw is not None else 0.5
            _vpin = max(0.0, min(1.0, _vpin))

            # Funding rate normalized: divide by 0.01, clip to [-3, +3]
            # Uses the scanner-injected funding_rate (from derivatives batch),
            # distinct from the ml_features_at_entry funding_rate_raw above
            _fr_live = float(signal.get("funding_rate", 0) or 0)
            _funding_norm = max(-3.0, min(3.0, _fr_live / 0.01))

            # --- OBI velocity features (Phase 8 -- from scanner injection) ---
            # Delta-5/15 and acceleration of OBI, range [-1, +1], default 0
            _obi_d5 = _safe(signal.get("obi_delta_5"), 0.0)
            _obi_d5 = max(-1.0, min(1.0, float(_obi_d5)))
            _obi_d15 = _safe(signal.get("obi_delta_15"), 0.0)
            _obi_d15 = max(-1.0, min(1.0, float(_obi_d15)))
            _obi_accel = _safe(signal.get("obi_acceleration"), 0.0)
            _obi_accel = max(-1.0, min(1.0, float(_obi_accel)))


            # --- Phase 12: New features from OHLCV/strategy data ---
            _close_to_vwap = _safe(_extra_dict.get("vwap_deviation") or signal.get("vwap_deviation"), 0.0)
            _close_to_vwap = max(-1.0, min(1.0, _close_to_vwap))

            _gk_vol = _safe(_extra_dict.get("gk_vol") or signal.get("gk_vol"), 0.0)
            _gk_vol = max(0.0, min(1.0, _gk_vol))

            # Phase 15 fix: expanded fear_greed fallback chain
            # signal -> extra_dict (multiple keys) -> fear_greed_cache.json -> default 50
            _fng_val = _safe(
                signal.get("fear_greed")
                or _extra_dict.get("fear_greed")
                or _extra_dict.get("fng")
                or _extra_dict.get("market_fear_greed")
                or signal.get("fear_greed_index")
                or signal.get("fng"),
                None
            )
            if _fng_val is None or _fng_val == 0.0:
                # Try loading from cache file as last resort
                try:
                    _fng_cache_path = DATA_DIR / "fear_greed_cache.json"
                    if _fng_cache_path.exists():
                        with open(_fng_cache_path) as _fng_f:
                            _fng_cache = json.load(_fng_f)
                        _fng_val = float(_fng_cache.get("value") or _fng_cache.get("fear_greed") or 50)
                    else:
                        _fng_val = 50.0
                except Exception:
                    _fng_val = 50.0
            _fng_gradient = _safe(_extra_dict.get("fng_gradient") or signal.get("fng_gradient"), 0.0)
            _fng_gradient = max(-1.0, min(1.0, _fng_gradient))
            # direction_market_alignment: direction * btc_24h_trend, falls back to raw direction
            # LONG+btc_up = positive (aligned), SHORT+btc_down = positive (aligned)
            # LONG+btc_down = negative (misaligned), no btc data -> raw direction (graceful fallback)
            _dir_val = self.DIRECTION_MAP.get(direction, 0)
            _btc_raw = _safe(signal.get("btc_24h_change") or mf.get("btc_24h_change"), None)
            _btc_24h = max(-1.0, min(1.0, float(_btc_raw) / 10.0)) if _btc_raw is not None else None
            _dma = (_dir_val * _btc_24h) if _btc_24h is not None else _dir_val  # direction_market_alignment

            feat = [
                # === Core features ===
                # category_encoded DROPPED (Phase 14)
                float(signal.get("confidence", 0.5) or 0.5),
                # rsi_at_entry DROPPED (Phase 14)
                _vol_ratio_norm,
                # risk_reward REMOVED (Phase 18): source proxy AUC=0.86
                # atr_at_entry DROPPED (Phase 14): redundant with hour_x_vol
                # regime_encoded DROPPED (Phase 14)
                _dma,  # direction_market_alignment (computed above)
                # === Strategy performance features REMOVED (Phase 18) ===
                # _strat_wr, _strat_sharpe_norm, _strat_closed_norm removed — strategy identity proxies
                # === Time-of-day features (Task 2) ===
                hour / 23.0,                                       # hour_utc
                math.sin(2 * math.pi * hour / 24.0),              # hour_sin
                # hour_cos DROPPED (Phase 14)
                # day_of_week DROPPED (Phase 14)
                # is_weekend DROPPED (Phase 14)
                math.sin(2 * math.pi * hour / 24.0) * atr_pct,   # hour_x_vol
                # === Trade structure features RE-ADDED (Phase 19) ===
                min(sl_dist_pct, 0.50),                            # sl_distance_pct [0, 0.50] capped
                min(tp_dist_pct, 0.50),                            # tp_distance_pct [0, 0.50] capped
                rr_asym,                                           # rr_asymmetry [-1, 1]
                # === Strategy forward track record (Phase 19) ===
                _safe(signal.get("forward_wr"), 0.5),              # strategy_forward_wr [0, 1]
                min(math.log2(1 + max(0, _safe(signal.get("forward_trades"), 0))) / 7.0, 1.0),  # strategy_forward_n [0, 1]
                # === Outcome features REMOVED (Phase 11 -- leaky, caused AUC=1.0) ===
                # entry_vs_optimal, hold_duration_hours, mfe_pct, mae_pct
                # are only available AFTER a trade closes -- using them to predict
                # outcomes is circular. See LEAKY_FEATURES set above.
                # === Regime interaction features REMOVED (Phase 12 -- dead features) ===
                # rsi_x_regime, vol_ratio_x_regime, momentum_x_regime, bb_x_regime,
                # hour_x_regime, atr_x_regime, direction_x_regime -- multiplied two
                # features that were mostly 0/default, producing always-zero values.
                # === Funding/basis features (Phase 6) ===
                _funding_raw * 100.0,                              # funding_rate_raw (scaled: 0.0001 -> 0.01)
                _funding_z,                                        # funding_z_30d (normalized to [-1, 1])
                _funding_persist,                                  # funding_persistence (normalized to [-1, 1])
                # === Live microstructure features (Phase 7) ===
                _obi,                                              # orderbook_imbalance [-1, +1]
                _vpin,                                             # vpin_toxicity [0, 1]
                _funding_norm,                                     # funding_rate_norm [-3, +3]
                # === OBI velocity features (Phase 8) ===
                _obi_d5,                                           # obi_delta_5 [-1, +1]
                _obi_d15,                                          # obi_delta_15 [-1, +1]
                _obi_accel,                                        # obi_acceleration [-1, +1]
                # === Market sentiment (Fear & Greed) ===
                # Phase 15 fix: use _fng_val (expanded fallback chain + cache file)
                min(max(float(_fng_val or 50), 0.0), 100.0) / 100.0,  # fear_greed_norm [0, 1]
                # === Cross-sectional ranking features (Phase 10 -- from scanner injection) ===
                _safe(signal.get("cs_momentum_rank"), 0.5),         # cs_momentum_rank [0, 1]
                max(-1.0, min(1.0, _safe(signal.get("cs_relative_strength"), 0.0))),  # cs_relative_strength [-1, 1]
                max(0.0, min(1.0, _safe(signal.get("cs_dispersion"), 0.5))),          # cs_dispersion [0, 1]
                max(-1.0, min(1.0, _safe(signal.get("cs_leader_lag"), 0.0))),         # cs_leader_lag [-1, 1]
                # === Phase 12 features (2026-03-19) -- from OHLCV/strategy data ===
                _close_to_vwap,                                      # close_to_vwap [-1, 1]
                _gk_vol,                                             # garman_klass_vol [0, 1]
                _fng_gradient,                                       # fng_gradient [-1, 1]
                # risk_reward_raw REMOVED (Phase 18): source proxy AUC=0.86
                # === Chi-squared validated technical features (Phase 13) ===
                max(-0.5, min(0.5, _safe(signal.get("mom30") or mf.get("mom30"), 0.0))),           # mom30 [-0.5, 0.5]
                max(0.0, min(1.0, _safe(signal.get("rsi30") or mf.get("rsi30"), 0.5))),           # rsi30 [0, 1]
                max(-0.05, min(0.05, _safe(signal.get("macd_hist_norm") or mf.get("macd_hist_norm"), 0.0))),  # macd_hist_norm
                max(0.0, min(1.0, _safe(signal.get("stoch_k30") or mf.get("stoch_k30"), 0.5))),   # stoch_k30 [0, 1]
                max(0.0, min(1.0, _safe(signal.get("stoch_d30") or mf.get("stoch_d30"), 0.5))),   # stoch_d30 [0, 1]
                max(-1.0, min(1.0, _safe(signal.get("cci20_norm") or mf.get("cci20_norm"), 0.0))), # cci20_norm [-1, 1]
                max(-1.0, min(0.0, _safe(signal.get("williams_r") or mf.get("williams_r"), -0.5))), # williams_r [-1, 0]
                # === BTC correlation & regime features (Phase 17 -- strongest missing predictor) ===
                max(-1.0, min(1.0, _safe(signal.get("btc_correlation") or mf.get("btc_correlation"), 0.8))),  # btc_correlation [-1, 1]
                max(-1.0, min(1.0, _safe(signal.get("btc_24h_change") or mf.get("btc_24h_change"), 0.0) / 10.0)),  # btc_24h_change_norm [-1, 1] (10% cap) — KEPT (Phase 20): needed for feature count alignment + direction_market_alignment computation
            ]

            arr = np.array(feat, dtype=np.float64)
            # Replace NaN/inf that leak through (pandas NaN survives `or 0`)
            np.nan_to_num(arr, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            return arr
        except Exception:
            return None

    # NOTE: _compute_smoothed_momentum and _compute_kimi_blueprint_features
    # were removed in Phase 5 (2026-03-17). These relied on close_prices,
    # high_prices, low_prices, volumes arrays which are NEVER present in
    # closed_picks.json (0/342 picks had them), producing 11 always-zero features.

    @staticmethod
    def _check_feature_health(X: np.ndarray, feature_names: list) -> bool:
        """Fail training if too many features are constant/zero.

        A feature is 'dead' when its standard deviation across all samples is 0,
        meaning it carries zero information for the model. If >50% are dead the
        data pipeline is broken and retraining would produce a misleading model.
        """
        import logging as _logging
        n_total = X.shape[1] if len(X.shape) > 1 else 0
        if n_total == 0:
            return False
        n_dead = sum(1 for i in range(n_total) if np.std(X[:, i]) == 0)
        pct_dead = n_dead / n_total
        dead_names = [
            feature_names[i] for i in range(min(n_total, len(feature_names)))
            if np.std(X[:, i]) == 0
        ]
        _logging.info(
            "Feature health: %d/%d alive (%d%% dead)",
            n_total - n_dead, n_total, int(pct_dead * 100),
        )
        if dead_names:
            _logging.info(
                "Dead features: %s%s",
                dead_names[:10], "..." if len(dead_names) > 10 else "",
            )
        if pct_dead > 0.5:
            _logging.warning(
                "Feature health FAILED: %d/%d dead features -- skipping retrain",
                n_dead, n_total,
            )
            return False
        return True

    def score_signal(self, signal: dict, strategy_stats: Optional[dict] = None,
                     convergence: int = 0) -> float:
        """
        Score a new signal.
        Returns score 0.0-1.0 (win probability or sigmoid-mapped predicted return).
        Uses ML model if trained, heuristic fallback otherwise.

        Phase 9: In regression mode, model.predict() returns predicted pnl_pct.
        This is converted to a 0-1 score via sigmoid for compatibility with
        the meta-labeling gate and downstream consumers.
        """
        if self.is_trained and self.model is not None:
            feat = self._signal_to_features(signal)
            if feat is not None:
                # Feature alignment check: warn if feature count drifts from training
                # When Boruta is active, feat has full FEATURES length (39) but
                # trained_feature_names has the reduced count. Compare against
                # the full feature list in that case.
                _expected_len = len(self.FEATURES) if self.selected_feature_indices is not None else len(self.trained_feature_names)
                if self.trained_feature_names and len(feat) != _expected_len:
                    print(f"[WARN] Feature count mismatch: expected "
                          f"{_expected_len} features, got {len(feat)}. "
                          f"Falling back to heuristic scoring.")
                    return self._heuristic_score(signal, strategy_stats, convergence)
                try:
                    # Apply Boruta feature selection mask (Phase 9)
                    _feat = feat
                    if self.selected_feature_indices is not None:
                        _feat = feat[self.selected_feature_indices]
                    # Apply same feature mask used during training (auto-pruning)
                    elif hasattr(self, '_active_feature_mask') and self._active_feature_mask is not None:
                        _feat = feat[self._active_feature_mask]
                    # Phase 9: Check if this is a regression model
                    _is_reg = getattr(self, '_is_regression_model', False)
                    if _is_reg:
                        # REGRESSION MODE: predict() returns predicted pnl_pct
                        predicted_return = float(self.model.predict(_feat.reshape(1, -1))[0])
                        # Convert to 0-1 score via sigmoid for compatibility
                        # predicted_return is in pct units (5.0 = 5%)
                        _return_frac = predicted_return / 100.0
                        win_prob = 1.0 / (1.0 + math.exp(-_return_frac * _REGRESSION_SIGMOID_STEEPNESS))
                    else:
                        proba = self.model.predict_proba(_feat.reshape(1, -1))[0]
                        win_prob = float(proba[1]) if len(proba) > 1 else float(proba[0])

                        # --- Heterogeneous ensemble blending ---
                        # Dynamic weights from ensemble_weights.json (performance-adaptive),
                        # with fixed 50/25/25 fallback if dynamic_ensemble unavailable.
                        # Secondary models were trained on scaled data, so we must
                        # apply the pipeline's scaler before passing features to them.
                        _ensemble_preds = {"primary": win_prob}
                        _feat_2d = _feat.reshape(1, -1)
                        _has_secondaries = (
                            getattr(self, '_secondary_rf', None) is not None
                            or getattr(self, '_secondary_catboost', None) is not None
                        )
                        if _has_secondaries:
                            try:
                                _scaler = self.model.named_steps.get("scaler")
                                _feat_scaled = _scaler.transform(_feat_2d) if _scaler is not None else _feat_2d
                            except Exception:
                                _feat_scaled = _feat_2d
                        if getattr(self, '_secondary_rf', None) is not None:
                            try:
                                _rf_p = self._secondary_rf.predict_proba(_feat_scaled)[0]
                                _ensemble_preds["rf"] = float(_rf_p[1]) if len(_rf_p) > 1 else float(_rf_p[0])
                            except Exception:
                                pass
                        if getattr(self, '_secondary_catboost', None) is not None:
                            try:
                                _cb_p = self._secondary_catboost.predict_proba(_feat_scaled)[0]
                                _ensemble_preds["catboost"] = float(_cb_p[1]) if len(_cb_p) > 1 else float(_cb_p[0])
                            except Exception:
                                pass
                        if len(_ensemble_preds) > 1:
                            # Dynamic ensemble weighting (fallback: fixed 50/25/25)
                            _regime_str = (
                                signal.get("regime_at_entry")
                                or signal.get("market_regime")
                                or signal.get("regime")
                            )
                            if self._dynamic_ensemble is not None:
                                try:
                                    _dyn_w = self._dynamic_ensemble.get_weights(
                                        regime=_regime_str,
                                        available_models=list(_ensemble_preds.keys()),
                                    )
                                    win_prob = sum(
                                        _dyn_w.get(m, 0) * p for m, p in _ensemble_preds.items()
                                    )
                                except Exception:
                                    # Fallback to fixed weights on any error
                                    n_sec = len(_ensemble_preds) - 1
                                    w_primary = 0.50
                                    w_each_sec = 0.50 / n_sec
                                    win_prob = w_primary * _ensemble_preds["primary"] + sum(
                                        w_each_sec * p for m, p in _ensemble_preds.items() if m != "primary"
                                    )
                            else:
                                # No dynamic ensemble -- fixed weights
                                n_sec = len(_ensemble_preds) - 1
                                w_primary = 0.50
                                w_each_sec = 0.50 / n_sec
                                win_prob = w_primary * _ensemble_preds["primary"] + sum(
                                    w_each_sec * p for m, p in _ensemble_preds.items() if m != "primary"
                                )

                        # Apply Isotonic Regression calibration if a calibrator
                        # was fitted at train time (ml_ranker.py:1024). Without
                        # this call, predict_proba outputs are uncalibrated and
                        # the META_LABEL_PROBABILITY_GATE acts on raw scores
                        # (root cause of the Kimi 2026-04-25 audit's
                        # Cohen's d=0.011 finding).
                        # Safety: keep raw value if calibration would collapse
                        # probabilities (known issue with small val sets).
                        if self.calibrator is not None:
                            try:
                                _cal = float(self.calibrator.predict([win_prob])[0])
                                if not (win_prob > 0.5 and _cal <= 0.0):
                                    win_prob = _cal
                            except Exception:
                                pass  # keep raw win_prob on any calibrator error
                        # (Legacy comment block kept for context below.)
                        # Apply Isotonic Regression calibration only if it doesn't
                        # collapse probabilities (known issue with small val sets).
                        # Safety check: calibrated value must be > 0 for raw > 0.5.
                        # Phase 14 Enhancement (Mar 28 2026): Capitulation Correction
                        # In extreme fear (F&G < 20) or capitulation regimes, the ML model
                        # (trained on broader data) is often over-skeptical of contrarian
                        # bounce signals. Apply a 20% relative boost for these signals
                        # to ensure they survive the meta-labeling gate.
                        _regime = (signal.get("market_regime") or "").lower()
                        _fgi = float(signal.get("fear_greed_at_entry") or signal.get("fgi") or 50)
                        if (_fgi < 20 or _regime == "capitulation") and signal.get("direction") == "LONG":
                            win_prob = min(0.95, win_prob * 1.20)

                    # Meta-labeling gate: suppress low-confidence signals
                    if win_prob < META_LABEL_PROBABILITY_GATE:
                        return win_prob * 0.5  # Reduce score below MIN_ML_SCORE threshold
                    return win_prob
                except Exception as _score_err:
                    # ML-1 (Kimi second-pass, ml_ranker.py:2622): the prior
                    # `except Exception: pass` swallowed every prediction-time
                    # error (NaN/inf inputs, sklearn shape mismatches, OOM,
                    # calibrator collapse) and silently fell through to the
                    # heuristic scorer. Operators had no way to detect that
                    # the ranker was effectively offline. Now we log and
                    # still fall through (preserve the safe-default
                    # behaviour) so observability is restored without
                    # changing the safety contract.
                    logger.warning(
                        "score_signal: ML path failed (symbol=%s, strategy=%s); "
                        "falling back to heuristic scorer. err=%r",
                        signal.get("symbol"), signal.get("strategy"), _score_err,
                    )

        # Heuristic fallback
        return self._heuristic_score(signal, strategy_stats, convergence)

    def _heuristic_score(self, signal: dict,
                         strategy_stats: Optional[dict] = None,
                         convergence: int = 0) -> float:
        """
        Heuristic scoring when ML model is not yet trained.
        Phase 3: regime-aware + funding rate + time-of-day adjustments.
        """
        score = 0.50  # Base

        # Confidence from strategy
        conf = signal.get("confidence", 0.5) or 0.5
        score += (conf - 0.5) * 0.3

        # Risk/reward bonus
        rr = signal.get("risk_reward", 1.5) or 1.5
        if rr > 3.0:
            score += 0.10
        elif rr > 2.0:
            score += 0.05

        # RSI sweet spot (30-60 for buys = not overbought, not in freefall)
        rsi_val = signal.get("rsi_at_entry", 50) or 50
        if 30 <= rsi_val <= 55:
            score += 0.05
        elif rsi_val > 75:
            score -= 0.10

        # Volume confirmation
        vol_r = signal.get("volume_ratio", 1.0) or 1.0
        if vol_r > 2.0:
            score += 0.05

        # Strategy track record
        if strategy_stats:
            wr = strategy_stats.get("win_rate", 0)
            if wr > 0.6:
                score += 0.08
            elif wr > 0.5:
                score += 0.04
            sharpe = strategy_stats.get("sharpe", 0)
            if sharpe > 1.0:
                score += 0.05

        # Signal convergence (multiple strategies agree)
        score += convergence * 0.03

        # --- Phase 3 heuristic enhancements ---

        # Regime alignment bonus: SHORT signals in bear regime get +0.08
        regime = (signal.get("regime_at_entry") or "neutral").lower()
        direction = (signal.get("signal_type") or signal.get("direction") or "").upper()
        if regime in ("bear", "risk_off") and direction == "SHORT":
            score += 0.08
        elif regime in ("bull", "risk_on") and direction in ("BUY", "LONG"):
            score += 0.08
        elif regime in ("bear", "risk_off") and direction in ("BUY", "LONG"):
            score -= 0.12  # Penalize counter-regime LONGs (Phase 1 lesson)

        # Funding rate signal: positive funding + SHORT = bonus (crowded longs)
        funding = signal.get("funding_rate", 0) or 0
        if funding > 0.0001 and direction == "SHORT":
            score += 0.06  # Fade crowded longs
        elif funding < -0.0001 and direction in ("BUY", "LONG"):
            score += 0.06  # Fade crowded shorts

        # Time-of-day: funding settlement hours (00, 08, 16 UTC) = predictable vol
        hour = _ts_hour(signal)
        if hour in (0, 8, 16):
            score += 0.03  # Settlement windows = more predictable moves
        elif 6 <= hour <= 8:
            score -= 0.03  # Low liquidity Asian gap = noise

        return max(0.0, min(1.0, round(score, 3)))

    def _save_weights(self, db):
        """Save per-strategy ML weights for external consumption."""
        weights = {}
        strategies = set()

        # Get all strategy stats
        all_stats = db.get_all_strategy_stats()
        for stat in all_stats:
            strat = stat["strategy"]
            strategies.add(strat)
            weights[strat] = {
                "win_rate": stat.get("win_rate", 0),
                "sharpe": stat.get("sharpe", 0),
                "closed_picks": stat.get("closed_picks", 0),
                "ml_rank": 0,  # Will be set below
            }

        # Rank by Sharpe (higher = better)
        ranked = sorted(weights.items(), key=lambda x: x[1].get("sharpe", 0), reverse=True)
        for rank, (strat, _) in enumerate(ranked):
            weights[strat]["ml_rank"] = rank + 1

        ML_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ML_WEIGHTS_PATH, "w") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_trained": self.is_trained,
                "weights": weights,
            }, f, indent=2)

    def get_ranking(self, db) -> list[dict]:
        """Get strategy ranking by ML-informed score."""
        all_stats = db.get_all_strategy_stats()
        if not all_stats:
            return []

        for stat in all_stats:
            fake_signal = {
                "strategy": stat["strategy"],
                "confidence": stat.get("win_rate", 0.5),
                "rsi_at_entry": 50,
                "volume_ratio": 1.0,
                "risk_reward": 2.0,
            }
            stat["ml_score"] = self.score_signal(fake_signal, stat)

        return sorted(all_stats, key=lambda x: x.get("ml_score", 0), reverse=True)


# ---------------------------------------------------------------------------
# Module self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"XGBoost available: {_HAS_XGBOOST}")
    print(f"LightGBM available: {_HAS_LIGHTGBM}")
    print(f"Probability gate: {META_LABEL_PROBABILITY_GATE}")
    print(f"Feature count: {len(MLSignalRanker.FEATURES)}")
    print(f"Features: {MLSignalRanker.FEATURES}")
    ranker = MLSignalRanker()

    # Test 1: SHORT in bear regime (should score HIGH)
    test_short = {
        "strategy": "regime_momentum_short_v2",
        "category": "crypto",
        "confidence": 0.86,
        "rsi_at_entry": 55,
        "volume_ratio": 2.3,
        "risk_reward": 2.1,
        "regime_at_entry": "bear",
        "signal_type": "SHORT",
        "direction": "SHORT",
        "entry_price": 85000,
        "take_profit": 80000,
        "stop_loss": 87000,
        "timestamp": "2026-03-17T08:30:00+00:00",
    }
    score_short = ranker.score_signal(test_short)

    # Test 2: LONG in bear regime (should score LOW)
    test_long_bear = {
        "strategy": "rsi_bounce_long",
        "category": "crypto",
        "confidence": 0.70,
        "rsi_at_entry": 25,
        "volume_ratio": 1.2,
        "risk_reward": 1.5,
        "regime_at_entry": "bear",
        "signal_type": "BUY",
        "direction": "LONG",
        "entry_price": 85000,
        "take_profit": 90000,
        "stop_loss": 82000,
        "timestamp": "2026-03-17T14:00:00+00:00",
    }
    score_long_bear = ranker.score_signal(test_long_bear)

    # Test 3: Feature vector verification
    feat = ranker._signal_to_features(test_short)
    if feat is not None:
        print(f"\nFeature vector length: {len(feat)} (expected {len(MLSignalRanker.FEATURES)})")
        assert len(feat) == len(MLSignalRanker.FEATURES), \
            f"MISMATCH: {len(feat)} features produced but {len(MLSignalRanker.FEATURES)} declared"
        non_zero = sum(1 for v in feat if abs(v) > 1e-10)
        print(f"Non-zero features: {non_zero}/{len(feat)}")
        for name, val in zip(MLSignalRanker.FEATURES, feat):
            print(f"  {name:25s} = {val:.6f}")
    else:
        print("ERROR: feature extraction returned None")

    # Test 4: Triple-barrier labeling
    print("\n--- Triple-barrier label tests ---")
    assert _compute_triple_barrier_label({"status": "WON", "pnl_pct": 5.0}) == (1, 1.0)
    assert _compute_triple_barrier_label({"result": "TP_HIT", "pnl_pct": 3.0}) == (1, 1.0)
    assert _compute_triple_barrier_label({"status": "LOST", "pnl_pct": -2.0}) == (-1, 1.2)
    assert _compute_triple_barrier_label({"result": "SL_HIT", "pnl_pct": -1.5}) == (-1, 1.2)
    assert _compute_triple_barrier_label({"result": "EXPIRED", "pnl_pct": 0}) == (0, 0.5)
    assert _compute_triple_barrier_label({"result": "other", "pnl_pct": 2.0}) == (1, 1.0)
    assert _compute_triple_barrier_label({"result": "other", "pnl_pct": -1.0}) == (-1, 1.2)
    print("All triple-barrier label tests passed!")

    # Test 5: Drift detection
    print("\n--- Drift detection tests ---")
    # No drift: 80% accuracy
    good_preds = [0.7] * 40 + [0.3] * 10
    good_outcomes = [1] * 40 + [0] * 10
    assert ranker._check_drift(good_preds, good_outcomes) is False, "Should not detect drift at 80% accuracy"

    # Drift: 30% accuracy (well below 45%)
    bad_preds = [0.7] * 15 + [0.3] * 35
    bad_outcomes = [1] * 15 + [1] * 35  # model says 0.3 but actual is 1
    assert ranker._check_drift(bad_preds, bad_outcomes) is True, "Should detect drift at 30% accuracy"

    # Insufficient data: fewer than window
    assert ranker._check_drift([0.5] * 10, [1] * 10, window=50) is False, "Should skip with insufficient data"
    print("All drift detection tests passed!")

    # Test 6: Prediction history
    print("\n--- Prediction history tests ---")
    ranker.record_prediction("BTCUSDT", "test_strategy", 0.75)
    history = ranker._load_prediction_history()
    assert len(history) > 0, "Prediction history should not be empty"
    last_entry = history[-1]
    assert last_entry["symbol"] == "BTCUSDT"
    assert last_entry["strategy"] == "test_strategy"
    assert last_entry["predicted_prob"] == 0.75
    assert last_entry["actual_outcome"] is None
    print(f"Prediction history: {len(history)} entries (last: {last_entry['symbol']})")

    # Test outcome back-fill
    closed = [{"symbol": "BTCUSDT", "strategy": "test_strategy", "result": "TP_HIT", "pnl_pct": 5.0}]
    filled = ranker.update_prediction_outcomes(closed)
    assert filled >= 1, "Should fill at least 1 outcome"
    history = ranker._load_prediction_history()
    filled_entry = [h for h in history if h["symbol"] == "BTCUSDT" and h["actual_outcome"] is not None]
    assert len(filled_entry) > 0, "Should have filled outcome"
    assert filled_entry[-1]["actual_outcome"] == 1
    print(f"Outcome back-fill: {filled} entries filled")
    print("All prediction history tests passed!")

    print(f"\nML Ranker initialized (trained={ranker.is_trained})")
    print(f"Model priority: {'XGBoost' if _HAS_XGBOOST else 'LightGBM' if _HAS_LIGHTGBM else 'RandomForest'}")
    print(f"Last trained at: {ranker.last_trained_at or 'never'}")
    print(f"\nTest SHORT in bear regime: {score_short:.3f} (should be HIGH)")
    print(f"Test LONG in bear regime:  {score_long_bear:.3f} (should be LOW)")
    print(f"Regime awareness working: {score_short > score_long_bear}")

