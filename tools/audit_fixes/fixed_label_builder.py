"""
Fixed-Threshold Label Builder
==============================
Replaces the broken adaptive positive-rate labeling that caused ALL 793 models
to produce AUC 0.25-0.28 (near random).

Root Cause (from AUDIT.md):
  The adaptive_target_min=0.15, adaptive_target_max=0.30 settings were supposed
  to control positive rates, but in practice produced 45-50% positive rates across
  all pairs — making the target a coin flip. A model learning to predict a 50/50
  label learns NOTHING useful.

Fix:
  Use fixed-threshold triple barrier labeling that produces 15-20% positive rates.
  This is the approach described in Lopez de Prado (2018) "Advances in Financial ML"
  without the adaptive contamination.

Expected outcome: positive_rate ≈ 0.15-0.22 (varies by volatility regime)
This provides SIGNAL. 50% positive rates provide NOISE.

Author: Forensic Audit Implementation (PR #72)
Date: 2026-04-11
"""
import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_fixed_labels(
    close: np.ndarray,
    atr: np.ndarray,
    tp_atr_mult: float = 2.0,
    sl_atr_mult: float = 1.0,
    max_hold_bars: int = 24,
    min_positive_rate: float = 0.10,
    max_positive_rate: float = 0.25,
) -> Tuple[np.ndarray, Dict]:
    """
    Fixed-threshold triple barrier labeling.
    
    For each bar, look forward up to max_hold_bars:
    - If price hits TP (entry + tp_atr_mult * ATR) FIRST → label = 1 (winner)
    - If price hits SL (entry - sl_atr_mult * ATR) FIRST → label = 0 (loser)
    - If neither within max_hold_bars → label = 0 (timeout = loser)
    
    The key difference from the broken adaptive approach:
    - TP and SL are FIXED multiples of ATR at each bar
    - We do NOT adjust thresholds to target a positive rate
    - Natural positive rate of ~15-20% emerges from the 2:1 TP/SL asymmetry
    
    Args:
        close: Array of close prices
        atr: Array of ATR values (same length as close)
        tp_atr_mult: Take-profit as multiple of ATR (default 2.0)
        sl_atr_mult: Stop-loss as multiple of ATR (default 1.0)
        max_hold_bars: Maximum bars to look forward
        min_positive_rate: Warn if positive rate falls below this
        max_positive_rate: Warn if positive rate exceeds this
        
    Returns:
        Tuple of (labels array, metadata dict)
    """
    n = len(close)
    assert len(atr) == n, f"close and atr must have same length: {n} vs {len(atr)}"
    
    labels = np.zeros(n, dtype=np.int32)
    exit_types = np.empty(n, dtype=object)
    exit_bars = np.zeros(n, dtype=np.int32)
    pnl_pcts = np.zeros(n, dtype=np.float64)
    
    for i in range(n - max_hold_bars):
        entry = close[i]
        current_atr = atr[i]
        
        if current_atr <= 0 or entry <= 0:
            labels[i] = 0
            exit_types[i] = "invalid"
            continue
        
        tp_price = entry + tp_atr_mult * current_atr
        sl_price = entry - sl_atr_mult * current_atr
        
        hit_type = "timeout"
        hit_bar = max_hold_bars
        
        for j in range(1, max_hold_bars + 1):
            if i + j >= n:
                break
            
            future_price = close[i + j]
            
            # Check TP first (if same bar hits both, TP wins — optimistic)
            if future_price >= tp_price:
                labels[i] = 1
                hit_type = "tp"
                hit_bar = j
                pnl_pcts[i] = (tp_price - entry) / entry
                break
            
            # Check SL
            if future_price <= sl_price:
                labels[i] = 0
                hit_type = "sl"
                hit_bar = j
                pnl_pcts[i] = (sl_price - entry) / entry
                break
        else:
            # Timeout — mark to market at max_hold_bars
            if i + max_hold_bars < n:
                exit_price = close[i + max_hold_bars]
                pnl_pcts[i] = (exit_price - entry) / entry
                # Timeout is labeled as 0 (not a winner)
                labels[i] = 0
                hit_type = "timeout"
        
        exit_types[i] = hit_type
        exit_bars[i] = hit_bar
    
    # Mark the last max_hold_bars as unlabeled (can't look forward)
    for i in range(max(0, n - max_hold_bars), n):
        labels[i] = -1  # -1 = unlabeled (exclude from training)
        exit_types[i] = "unlabeled"
    
    # Compute statistics
    labeled_mask = labels >= 0
    n_labeled = labeled_mask.sum()
    n_positive = (labels == 1).sum()
    positive_rate = n_positive / n_labeled if n_labeled > 0 else 0
    
    # Exit type distribution
    exit_counts = {}
    for et in ["tp", "sl", "timeout", "invalid", "unlabeled"]:
        exit_counts[et] = int((exit_types == et).sum())
    
    metadata = {
        "n_total": int(n),
        "n_labeled": int(n_labeled),
        "n_positive": int(n_positive),
        "n_negative": int(n_labeled - n_positive),
        "positive_rate": float(positive_rate),
        "tp_atr_mult": tp_atr_mult,
        "sl_atr_mult": sl_atr_mult,
        "max_hold_bars": max_hold_bars,
        "exit_distribution": exit_counts,
        "avg_bars_to_exit": float(exit_bars[labeled_mask].mean()) if n_labeled > 0 else 0,
        "avg_winner_pnl_pct": float(pnl_pcts[labels == 1].mean() * 100) if n_positive > 0 else 0,
        "avg_loser_pnl_pct": float(pnl_pcts[(labels == 0) & labeled_mask].mean() * 100)
            if (n_labeled - n_positive) > 0 else 0,
    }
    
    # Validate positive rate
    if positive_rate < min_positive_rate:
        logger.warning(
            f"Low positive rate: {positive_rate:.1%} < {min_positive_rate:.1%}. "
            f"Consider reducing tp_atr_mult ({tp_atr_mult}) or increasing sl_atr_mult ({sl_atr_mult})."
        )
    elif positive_rate > max_positive_rate:
        logger.warning(
            f"High positive rate: {positive_rate:.1%} > {max_positive_rate:.1%}. "
            f"Labels may be too easy. Consider increasing tp_atr_mult ({tp_atr_mult}) "
            f"or reducing sl_atr_mult ({sl_atr_mult})."
        )
    else:
        logger.info(
            f"Label stats: positive_rate={positive_rate:.1%}, "
            f"n_labeled={n_labeled}, tp_hits={exit_counts.get('tp', 0)}, "
            f"sl_hits={exit_counts.get('sl', 0)}, timeouts={exit_counts.get('timeout', 0)}"
        )
    
    return labels, metadata


def build_labels_for_pair(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    atr_period: int = 14,
    timeframe: str = "1h",
) -> Tuple[pd.Series, Dict]:
    """
    Convenience function: compute ATR and build labels from a DataFrame.
    
    Uses the recommended TP/SL configs from the audit per timeframe.
    
    Args:
        df: OHLC DataFrame
        close_col, high_col, low_col: Column names
        atr_period: Period for ATR calculation
        timeframe: "1h" or "4h" (determines TP/SL multipliers)
    """
    # ATR calculation
    tr = np.maximum(
        df[high_col] - df[low_col],
        np.maximum(
            abs(df[high_col] - df[close_col].shift(1)),
            abs(df[low_col] - df[close_col].shift(1))
        )
    )
    atr = tr.rolling(atr_period).mean().fillna(tr).values
    close = df[close_col].values
    
    # Timeframe-specific configs (from audit Section 5.2)
    configs = {
        "1h": {"tp_atr_mult": 2.5, "sl_atr_mult": 1.5, "max_hold_bars": 24},
        "4h": {"tp_atr_mult": 3.5, "sl_atr_mult": 2.0, "max_hold_bars": 20},
        "daily": {"tp_atr_mult": 2.0, "sl_atr_mult": 1.0, "max_hold_bars": 10},
    }
    
    config = configs.get(timeframe, configs["4h"])
    
    labels, metadata = build_fixed_labels(close, atr, **config)
    metadata["timeframe"] = timeframe
    
    return pd.Series(labels, index=df.index, name="label"), metadata


def validate_label_quality(
    labels: np.ndarray,
    min_samples: int = 200,
    min_positive_rate: float = 0.10,
    max_positive_rate: float = 0.30,
) -> Dict:
    """
    Validate that labels are suitable for training.
    
    Critical check: the old system had positive rates of 45-50%.
    This function ensures we don't repeat that mistake.
    
    Args:
        labels: Array of 0/1 labels (may contain -1 for unlabeled)
        min_samples: Minimum labeled samples required
        min_positive_rate: Minimum acceptable positive rate
        max_positive_rate: Maximum acceptable positive rate
        
    Returns:
        Dict with verdict and details
    """
    labeled_mask = labels >= 0
    n_labeled = labeled_mask.sum()
    n_positive = (labels == 1).sum()
    positive_rate = n_positive / n_labeled if n_labeled > 0 else 0
    
    issues = []
    
    if n_labeled < min_samples:
        issues.append(
            f"Insufficient samples: {n_labeled} < {min_samples} minimum. "
            f"Need more data for reliable model training."
        )
    
    if n_positive < 30:
        issues.append(
            f"Insufficient positive samples: {n_positive} < 30. "
            f"Model cannot learn the positive class reliably."
        )
    
    if positive_rate < min_positive_rate:
        issues.append(
            f"Positive rate too low: {positive_rate:.1%} < {min_positive_rate:.1%}. "
            f"TP threshold may be too aggressive."
        )
    
    if positive_rate > max_positive_rate:
        issues.append(
            f"Positive rate too high: {positive_rate:.1%} > {max_positive_rate:.1%}. "
            f"⚠️ DANGER: This is the same problem as the old system! "
            f"Near-50% positive rates produce coin-flip targets. "
            f"Increase tp_atr_mult or decrease sl_atr_mult."
        )
    
    # Special warning for the 40%+ zone
    if positive_rate > 0.40:
        issues.append(
            f"🔴 CRITICAL: Positive rate {positive_rate:.1%} is in the coin-flip zone. "
            f"The old system had 45-50% positive rates and produced AUC 0.27. "
            f"DO NOT TRAIN on these labels."
        )
    
    verdict = "PASS" if len(issues) == 0 else "FAIL"
    
    return {
        "verdict": verdict,
        "n_labeled": int(n_labeled),
        "n_positive": int(n_positive),
        "n_negative": int(n_labeled - n_positive),
        "positive_rate": float(positive_rate),
        "issues": issues,
    }
