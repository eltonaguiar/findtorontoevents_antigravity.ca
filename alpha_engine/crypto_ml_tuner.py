#!/usr/bin/env python3
"""
Crypto-specific ML hyperparameter tuning and hybrid model logic.

Provides optimized XGBoost parameters for crypto volatility, cross-asset
correlation analysis, retrain triggers, volatility-scaled confidence,
and hybrid equity-crypto signal logic.

stdlib only -- no external ML libraries required at import time.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


def get_crypto_xgboost_params() -> dict:
    """Return optimized XGBoost hyperparameters tuned for crypto volatility.

    Crypto markets are noisier than equities -- heavier regularization,
    shallower trees, and slower learning rate prevent overfitting on
    short-lived patterns.
    """
    return {
        "n_estimators": 200,         # More trees for noisy crypto
        "max_depth": 4,              # Shallower to prevent overfit on crypto noise
        "learning_rate": 0.05,       # Slower learning for volatile data
        "subsample": 0.7,            # More regularization
        "colsample_bytree": 0.6,     # Feature subsampling
        "min_child_weight": 10,      # Larger minimum to reduce noise sensitivity
        "gamma": 0.3,                # Pruning threshold higher for crypto
        "reg_alpha": 0.5,            # L1 regularization
        "reg_lambda": 2.0,           # L2 regularization (higher for crypto)
        "scale_pos_weight": 1.0,     # Adjust based on class balance
    }


def compute_cross_asset_correlation(
    crypto_returns: list[float],
    equity_returns: list[float],
    window: int = 30,
) -> float:
    """Pearson correlation between crypto and equity returns over rolling window.

    When correlation > 0.7: crypto follows equities (use equity signals as confirmation).
    When correlation < 0.3: crypto is independent (ignore equity signals).

    Args:
        crypto_returns: Daily returns for crypto asset.
        equity_returns: Daily returns for equity index (e.g. SPY).
        window: Rolling window size (default 30 days).

    Returns:
        Pearson correlation coefficient in [-1, 1], or 0.0 on insufficient data.
    """
    if not crypto_returns or not equity_returns:
        return 0.0

    # Use the last `window` observations from each series
    c = crypto_returns[-window:]
    e = equity_returns[-window:]

    # Align lengths
    n = min(len(c), len(e))
    if n < 5:
        return 0.0  # Not enough data for meaningful correlation

    c = c[-n:]
    e = e[-n:]

    # Compute means
    c_mean = sum(c) / n
    e_mean = sum(e) / n

    # Compute Pearson r
    cov = sum((ci - c_mean) * (ei - e_mean) for ci, ei in zip(c, e))
    c_var = sum((ci - c_mean) ** 2 for ci in c)
    e_var = sum((ei - e_mean) ** 2 for ei in e)

    denom = math.sqrt(c_var * e_var)
    if denom < 1e-12:
        return 0.0

    return cov / denom


def should_force_retrain(
    model_metadata: dict,
    closed_picks: list[dict],
) -> bool:
    """Determine if the ML model should be force-retrained.

    Returns True if any of these conditions hold:
    - Last retrain was more than 7 days ago
    - Rolling 50-pick win rate dropped below 40%
    - Regime changed since last retrain (bull <-> bear)
    - Feature importance distribution shifted (top feature changed)
    - More than 100 new closed picks since last retrain

    Args:
        model_metadata: Dict with keys like 'last_retrain_ts', 'regime_at_retrain',
                        'top_feature', 'picks_at_retrain'.
        closed_picks: List of closed pick dicts with 'status' and 'exit_date'.

    Returns:
        True if retrain is recommended.
    """
    if not model_metadata:
        return True  # No model metadata means never trained

    # Condition 1: Last retrain > 7 days ago
    last_retrain_str = model_metadata.get("last_retrain_ts", "")
    if last_retrain_str:
        try:
            last_retrain = datetime.fromisoformat(last_retrain_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_retrain > timedelta(days=7):
                return True
        except (ValueError, TypeError):
            return True  # Can't parse date -- retrain to be safe
    else:
        return True  # No timestamp recorded

    # Condition 2: Rolling 50-pick WR dropped below 40%
    if len(closed_picks) >= 50:
        recent_50 = closed_picks[-50:]
        wins = sum(1 for p in recent_50 if p.get("status") == "WON")
        if wins / 50 < 0.40:
            return True

    # Condition 3: Regime changed since last retrain
    current_regime = _detect_current_regime(closed_picks)
    retrain_regime = model_metadata.get("regime_at_retrain", "")
    if retrain_regime and current_regime and retrain_regime != current_regime:
        # Only trigger on major shifts: bull<->bear
        major_shifts = {
            ("bull", "bear"), ("bear", "bull"),
            ("bullish", "bearish"), ("bearish", "bullish"),
        }
        if (retrain_regime.lower(), current_regime.lower()) in major_shifts:
            return True

    # Condition 4: Top feature changed
    current_top_feature = model_metadata.get("current_top_feature", "")
    retrain_top_feature = model_metadata.get("top_feature", "")
    if (current_top_feature and retrain_top_feature
            and current_top_feature != retrain_top_feature):
        return True

    # Condition 5: More than 100 new closed picks since last retrain
    picks_at_retrain = model_metadata.get("picks_at_retrain", 0)
    if len(closed_picks) - picks_at_retrain > 100:
        return True

    return False


def _detect_current_regime(closed_picks: list[dict]) -> str:
    """Infer current market regime from recent closed pick outcomes.

    Simple heuristic: if recent 20 picks have >60% WR and positive avg PnL,
    regime is 'bull'. If <35% WR and negative avg PnL, regime is 'bear'.
    Otherwise 'neutral'.
    """
    if len(closed_picks) < 10:
        return "neutral"

    recent = closed_picks[-20:]
    wins = sum(1 for p in recent if p.get("status") == "WON")
    wr = wins / len(recent)
    avg_pnl = sum(p.get("pnl_pct", 0) or 0 for p in recent) / len(recent)

    if wr > 0.60 and avg_pnl > 0:
        return "bull"
    elif wr < 0.35 and avg_pnl < 0:
        return "bear"
    return "neutral"


def apply_crypto_volatility_scaling(
    predictions: list[dict],
    current_atr: float,
    median_atr: float,
) -> list[dict]:
    """Scale prediction confidence based on volatility regime.

    - High vol (ATR > 2x median): reduce confidence by 20% (more noise)
    - Low vol (ATR < 0.5x median): reduce confidence by 10% (breakout risk)
    - Normal vol: no adjustment

    Args:
        predictions: List of signal dicts with 'confidence' key.
        current_atr: Current ATR value.
        median_atr: Median ATR over lookback period.

    Returns:
        Modified predictions list with adjusted confidence values.
    """
    if not predictions or median_atr <= 0:
        return predictions

    atr_ratio = current_atr / median_atr

    if atr_ratio > 2.0:
        # High volatility -- reduce confidence by 20%
        scale = 0.80
        reason = f"high_vol (ATR {atr_ratio:.1f}x median)"
    elif atr_ratio < 0.5:
        # Low volatility -- reduce confidence by 10% (breakout risk)
        scale = 0.90
        reason = f"low_vol (ATR {atr_ratio:.1f}x median)"
    else:
        return predictions  # Normal vol, no adjustment

    for pred in predictions:
        original = pred.get("confidence", 0.5)
        pred["confidence"] = round(original * scale, 4)
        pred["vol_scaling"] = reason
        pred["vol_scaling_factor"] = scale

    return predictions


def hybrid_equity_crypto_signal(
    crypto_signal: dict,
    equity_regime: str,
    correlation: float,
) -> dict:
    """Adjust crypto signal based on equity market regime and cross-asset correlation.

    When crypto-equity correlation > 0.7 AND equity regime is bearish:
      -> downgrade crypto LONG signals (reduce confidence by 30%)
    When correlation < 0.3:
      -> ignore equity regime entirely (crypto is independent)

    Args:
        crypto_signal: Signal dict with 'signal_type' and 'confidence'.
        equity_regime: One of 'bull', 'bear', 'neutral'.
        correlation: Cross-asset correlation coefficient.

    Returns:
        Modified signal dict.
    """
    if not crypto_signal:
        return crypto_signal

    sig_type = crypto_signal.get("signal_type", "BUY").upper()

    # Low correlation -- crypto is independent, ignore equity regime
    if correlation < 0.3:
        crypto_signal["equity_regime_applied"] = False
        crypto_signal["equity_regime_note"] = (
            f"Correlation {correlation:.2f} < 0.3: crypto independent, equity regime ignored"
        )
        return crypto_signal

    # High correlation -- crypto follows equities
    if correlation > 0.7:
        if equity_regime.lower() in ("bear", "bearish") and sig_type == "BUY":
            original = crypto_signal.get("confidence", 0.5)
            crypto_signal["confidence"] = round(original * 0.70, 4)
            crypto_signal["equity_regime_applied"] = True
            crypto_signal["equity_regime_note"] = (
                f"Corr {correlation:.2f} > 0.7 + equity bearish: "
                f"LONG downgraded {original:.2f} -> {crypto_signal['confidence']:.2f}"
            )
        elif equity_regime.lower() in ("bull", "bullish") and sig_type == "BUY":
            # Equity bullish + high correlation = confirmation
            crypto_signal["equity_regime_applied"] = True
            crypto_signal["equity_regime_note"] = (
                f"Corr {correlation:.2f} > 0.7 + equity bullish: LONG confirmed"
            )
        else:
            crypto_signal["equity_regime_applied"] = False
    else:
        # Mid-range correlation (0.3-0.7): no strong adjustment
        crypto_signal["equity_regime_applied"] = False
        crypto_signal["equity_regime_note"] = (
            f"Correlation {correlation:.2f} in neutral zone (0.3-0.7)"
        )

    return crypto_signal
