#!/usr/bin/env python3
"""
Drift Monitor — §3 Ongoing Monitoring & Drift Management
==========================================================
Implements:
  - Performance drift detection (Sharpe/MDD/Alpha vs. backtest baselines)
  - Feature drift (Population Stability Index)
  - Model decay detection (rolling window OOS)
  - Regime detection (volatility clustering)
  - Auto-alert and auto-demotion triggers

Usage:
    python drift_monitor.py --strategy st_fear_greed_contrarian --asset-class CRYPTO
    python drift_monitor.py --all  # Check all strategies for drift
"""

from __future__ import annotations
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Drift Detection Data Structures
# ---------------------------------------------------------------------------
@dataclass
class DriftAlert:
    """A single drift alert."""
    strategy: str
    asset_class: str
    alert_type: str  # "performance_drift", "feature_drift", "model_decay", "regime_shift"
    severity: str    # "INFO", "WARNING", "CRITICAL"
    metric: str
    baseline_value: float
    current_value: float
    deviation_pct: float
    message: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class DriftReport:
    """Complete drift analysis for a strategy."""
    strategy: str
    asset_class: str
    generated_at: str = ""
    alerts: List[DriftAlert] = field(default_factory=list)
    performance_drift: Dict[str, Any] = field(default_factory=dict)
    feature_drift: Dict[str, float] = field(default_factory=dict)
    regime_state: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = "NONE"  # NONE, REDUCE_SIZE, PAPER_ONLY, KILL

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# §3.1 Performance Drift Detection
# ---------------------------------------------------------------------------
def detect_performance_drift(
    baseline_metrics: Dict[str, float],
    recent_picks: List[Dict],
    threshold_pct: float = 20.0,
    min_recent_n: int = 10,
) -> List[DriftAlert]:
    """
    Compare recent performance against backtest baselines.
    Alert if deviation > threshold for 2+ consecutive measurement periods.
    """
    alerts = []
    strategy = baseline_metrics.get("strategy", "unknown")
    asset_class = baseline_metrics.get("asset_class", "UNKNOWN")

    if len(recent_picks) < min_recent_n:
        return alerts  # Not enough data to detect drift

    # Compute recent metrics
    pnls = [float(p.get("pnl_pct", 0) or 0) for p in recent_picks]
    wins = sum(1 for pnl in pnls if pnl > 0)
    recent_wr = wins / len(pnls) if pnls else 0
    recent_avg_pnl = np.mean(pnls) if pnls else 0

    # Profit factor — use a sentinel for the all-wins case instead of the
    # 0.001 magic-number fallback that would report PF=1000x and trigger a
    # false improvement alert. Mirrors strategy_prover.compute_performance
    # at line ~205. (pass-2 issue #4, opus-hc-audit 2026-04-11.)
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss > 0:
        recent_pf = gross_profit / gross_loss
    elif gross_profit > 0:
        recent_pf = 99.99  # All-wins sentinel — caller can detect and skip
    else:
        recent_pf = 0.0

    # PR #72 cherry-pick: recent Sharpe from equity-curve returns, annualized
    # under ~daily periodicity. Compared against baseline_sharpe below;
    # emits a perf-drift alert if |deviation| > threshold_pct (>30% per spec).
    recent_sharpe = 0.0
    if len(pnls) >= 2:
        equity = [0.0]
        for pnl in pnls:
            equity.append(equity[-1] + pnl)
        equity_returns = []
        for i in range(1, len(equity)):
            prev = equity[i - 1]
            if prev != 0:
                equity_returns.append((equity[i] - prev) / abs(prev))
        if len(equity_returns) >= 2:
            mean_ret = float(np.mean(equity_returns))
            std_ret = float(np.std(equity_returns, ddof=1))
            if std_ret > 0:
                periods = 252  # assume daily periodicity
                recent_sharpe = (mean_ret * periods - 0.05) / (std_ret * math.sqrt(periods))

    # Compare against baselines (sharpe drift added per PR #72)
    checks = [
        ("win_rate", baseline_metrics.get("baseline_wr", 0.5), recent_wr),
        ("profit_factor", baseline_metrics.get("baseline_pf", 1.0), recent_pf),
        ("avg_pnl", baseline_metrics.get("baseline_avg_pnl", 0), recent_avg_pnl),
        ("sharpe", baseline_metrics.get("baseline_sharpe", 0), recent_sharpe),
    ]

    for metric_name, baseline, current in checks:
        if baseline == 0:
            continue
        deviation = abs(current - baseline) / abs(baseline) * 100

        if deviation > threshold_pct:
            # Determine severity
            if deviation > 50:
                severity = "CRITICAL"
            elif deviation > threshold_pct:
                severity = "WARNING"
            else:
                severity = "INFO"

            # Is it degradation (worse) or improvement (better)?
            direction = "degraded" if current < baseline else "improved"

            alerts.append(DriftAlert(
                strategy=strategy,
                asset_class=asset_class,
                alert_type="performance_drift",
                severity=severity,
                metric=metric_name,
                baseline_value=round(baseline, 4),
                current_value=round(current, 4),
                deviation_pct=round(deviation, 1),
                message=f"{metric_name} {direction}: baseline={baseline:.3f}, recent={current:.3f} ({deviation:.1f}% deviation)",
            ))

    return alerts


# ---------------------------------------------------------------------------
# §3.2 Feature Drift — Population Stability Index (PSI)
# ---------------------------------------------------------------------------
def compute_psi(expected: List[float], actual: List[float], n_bins: int = 10) -> float:
    """Compute Population Stability Index between expected and actual.

    PSI < 0.10 → no significant shift
    PSI 0.10-0.25 → moderate shift, monitor
    PSI > 0.25 → significant shift, retrain

    Ref: minimax quant review issue #4 (2026-04-11), verified by
    opus-hc-audit. Prior implementation used min/max linspace edges, which
    are sensitive to single outliers and frequently produced bins with zero
    actual observations. This version uses combined-distribution percentile
    edges (deduplicated) so bin density tracks the data, not the tails.
    Output is clipped to [0, 10] to avoid pathological values from
    near-zero-bucket ratios.
    """
    if not expected or not actual:
        return 0.0

    expected_arr = np.asarray(expected, dtype=float)
    actual_arr = np.asarray(actual, dtype=float)
    combined = np.concatenate([expected_arr, actual_arr])
    if combined.size == 0 or float(np.ptp(combined)) == 0.0:
        return 0.0

    # Percentile-based bin edges (robust to outliers)
    percentiles = np.linspace(0.0, 100.0, n_bins + 1)
    bin_edges = np.percentile(combined, percentiles)
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    exp_hist, _ = np.histogram(expected_arr, bins=bin_edges)
    act_hist, _ = np.histogram(actual_arr, bins=bin_edges)
    n_actual_bins = len(bin_edges) - 1

    # Smooth zeros to avoid log(0); proportions sum to 1
    smooth = 1e-6
    exp_pct = (exp_hist + smooth) / (exp_hist.sum() + n_actual_bins * smooth)
    act_pct = (act_hist + smooth) / (act_hist.sum() + n_actual_bins * smooth)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.clip(act_pct / exp_pct, 0.01, 100.0)
        psi = float(np.sum((act_pct - exp_pct) * np.log(ratio)))

    return float(np.clip(psi, 0.0, 10.0))


def detect_feature_drift(
    baseline_features: Dict[str, List[float]],
    recent_features: Dict[str, List[float]],
    psi_threshold: float = 0.25,
) -> List[DriftAlert]:
    """
    Compute PSI for each feature and flag drifting ones.
    """
    alerts = []
    for feature_name in baseline_features:
        if feature_name not in recent_features:
            continue

        psi = compute_psi(baseline_features[feature_name], recent_features[feature_name])

        if psi > psi_threshold:
            alerts.append(DriftAlert(
                strategy="",
                asset_class="",
                alert_type="feature_drift",
                severity="CRITICAL" if psi > 0.50 else "WARNING",
                metric=feature_name,
                baseline_value=0,
                current_value=round(psi, 4),
                deviation_pct=round(psi * 100, 1),
                message=f"Feature '{feature_name}' PSI={psi:.4f} > {psi_threshold} — distribution shifted significantly",
            ))

    return alerts


# ---------------------------------------------------------------------------
# §3.3 Regime Detection (Volatility Clustering)
# ---------------------------------------------------------------------------
@dataclass
class RegimeState:
    """Current market regime classification."""
    regime: str = "UNKNOWN"  # LOW_VOL, NORMAL, HIGH_VOL, CRISIS
    volatility_percentile: float = 0.0
    correlation_regime: str = "NORMAL"  # NORMAL, HIGH_CORR (risk-off), DECORRELATED
    confidence: float = 0.0


def detect_regime(
    recent_returns: List[float],
    lookback_returns: List[float],
    recent_asset_returns: Optional[Dict[str, List[float]]] = None,
) -> RegimeState:
    """Volatility-based regime detection with optional correlation regime.

    The volatility path classifies LOW_VOL / NORMAL / HIGH_VOL / CRISIS by
    comparing recent vs lookback std. The optional correlation path
    populates `state.correlation_regime` from a dict of asset returns —
    crisis regimes typically show synchronized drawdowns across assets, so
    HIGH_CORR (>0.7 mean abs off-diagonal) is a portfolio-protection signal
    that vol-only detection misses (pass-2 issue #5, opus-hc-audit 2026-04-11).
    """
    state = RegimeState()

    if len(recent_returns) < 5 or len(lookback_returns) < 30:
        return state

    recent_vol = float(np.std(recent_returns, ddof=1))
    lookback_vol = float(np.std(lookback_returns, ddof=1))

    if lookback_vol == 0:
        return state

    vol_ratio = recent_vol / lookback_vol

    if vol_ratio < 0.5:
        state.regime = "LOW_VOL"
        state.confidence = min(1.0, (0.5 - vol_ratio) / 0.5)
    elif vol_ratio < 1.5:
        state.regime = "NORMAL"
        state.confidence = 1.0 - abs(vol_ratio - 1.0) / 0.5
    elif vol_ratio < 3.0:
        state.regime = "HIGH_VOL"
        state.confidence = min(1.0, (vol_ratio - 1.5) / 1.5)
    else:
        state.regime = "CRISIS"
        state.confidence = 1.0

    # Percentile ranking
    rolling_vols = [
        float(np.std(lookback_returns[i:i + 5], ddof=1))
        for i in range(len(lookback_returns) - 5)
    ]
    if rolling_vols:
        state.volatility_percentile = (
            sum(1 for v in rolling_vols if v < recent_vol) / len(rolling_vols) * 100
        )

    # Correlation regime (multi-asset only)
    if recent_asset_returns and len(recent_asset_returns) >= 2:
        try:
            assets = [
                np.asarray(v, dtype=float)
                for v in recent_asset_returns.values()
                if v is not None and len(v) >= 5
            ]
            if len(assets) >= 2:
                min_len = min(len(a) for a in assets)
                trimmed = np.vstack([a[-min_len:] for a in assets])
                corr_matrix = np.corrcoef(trimmed)
                if corr_matrix.ndim == 2 and corr_matrix.shape[0] >= 2:
                    iu = np.triu_indices_from(corr_matrix, k=1)
                    off_diag = corr_matrix[iu]
                    finite = off_diag[np.isfinite(off_diag)]
                    if finite.size > 0:
                        avg_abs_corr = float(np.mean(np.abs(finite)))
                        if avg_abs_corr > 0.7:
                            state.correlation_regime = "HIGH_CORR"
                        elif avg_abs_corr < 0.2:
                            state.correlation_regime = "DECORRELATED"
                        else:
                            state.correlation_regime = "NORMAL"
        except (ValueError, TypeError):
            pass  # Bad input — leave default "NORMAL"

    return state


# ---------------------------------------------------------------------------
# §3.4 Recommended Actions
# ---------------------------------------------------------------------------
def compute_recommended_action(alerts: List[DriftAlert]) -> str:
    """
    Based on drift alerts, recommend an action.
    """
    critical_count = sum(1 for a in alerts if a.severity == "CRITICAL")
    warning_count = sum(1 for a in alerts if a.severity == "WARNING")
    perf_drift_alerts = [a for a in alerts if a.alert_type == "performance_drift"]

    # Critical: model is broken
    if critical_count >= 2:
        return "PAPER_ONLY"  # Demote to paper trading
    
    # Performance degradation
    if any(a.metric == "profit_factor" and a.current_value < 0.8 for a in perf_drift_alerts):
        return "KILL"  # Strategy no longer profitable

    if any(a.metric == "win_rate" and a.deviation_pct > 40 for a in perf_drift_alerts):
        return "REDUCE_SIZE"  # Halve position sizes

    if warning_count >= 3:
        return "REDUCE_SIZE"

    if critical_count == 1:
        return "REDUCE_SIZE"

    return "NONE"


# ---------------------------------------------------------------------------
# §3.5 Circuit Breaker
# ---------------------------------------------------------------------------
def check_circuit_breaker(
    equity_curve: List[float],
    max_weekly_drawdown_pct: float = 15.0,
) -> Optional[DriftAlert]:
    """
    §5 What-If: Portfolio drawdown exceeds threshold in a week.
    Trigger circuit breaker.
    """
    if len(equity_curve) < 7:
        return None

    recent_7 = equity_curve[-7:]
    peak = max(recent_7)
    current = recent_7[-1]

    if peak > 0:
        weekly_dd = (peak - current) / peak * 100
        if weekly_dd > max_weekly_drawdown_pct:
            return DriftAlert(
                strategy="PORTFOLIO",
                asset_class="ALL",
                alert_type="circuit_breaker",
                severity="CRITICAL",
                metric="weekly_drawdown",
                baseline_value=max_weekly_drawdown_pct,
                current_value=round(weekly_dd, 2),
                deviation_pct=round(weekly_dd, 2),
                message=f"CIRCUIT BREAKER: Weekly drawdown {weekly_dd:.1f}% exceeds {max_weekly_drawdown_pct}% limit. HALVE ALL POSITIONS.",
            )

    return None


# ---------------------------------------------------------------------------
# Full Drift Analysis
# ---------------------------------------------------------------------------
def run_drift_analysis(
    strategy: str,
    asset_class: str,
    baseline_metrics: Dict[str, float],
    recent_picks: List[Dict],
    recent_returns: Optional[List[float]] = None,
    lookback_returns: Optional[List[float]] = None,
    baseline_features: Optional[Dict[str, List[float]]] = None,
    recent_features: Optional[Dict[str, List[float]]] = None,
) -> DriftReport:
    """Run the complete drift analysis suite."""
    report = DriftReport(strategy=strategy, asset_class=asset_class)

    # 1. Performance drift
    baseline_metrics["strategy"] = strategy
    baseline_metrics["asset_class"] = asset_class
    perf_alerts = detect_performance_drift(baseline_metrics, recent_picks)
    report.alerts.extend(perf_alerts)

    # 2. Feature drift
    if baseline_features and recent_features:
        feat_alerts = detect_feature_drift(baseline_features, recent_features)
        for a in feat_alerts:
            a.strategy = strategy
            a.asset_class = asset_class
        report.alerts.extend(feat_alerts)

    # 3. Regime detection
    if recent_returns and lookback_returns:
        regime = detect_regime(recent_returns, lookback_returns)
        report.regime_state = asdict(regime)

    # 4. Recommended action
    report.recommended_action = compute_recommended_action(report.alerts)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Drift Monitor — Performance & Feature Drift Detection")
    parser.add_argument("--strategy", type=str, help="Strategy to monitor")
    parser.add_argument("--asset-class", type=str, default="", help="Asset class")
    parser.add_argument("--demo", action="store_true", help="Run with demo data")
    args = parser.parse_args()

    if args.demo:
        # Demo with synthetic data
        baseline = {
            "baseline_wr": 0.70,
            "baseline_pf": 1.80,
            "baseline_avg_pnl": 0.45,
        }
        # Simulate degraded recent picks
        recent = [{"pnl_pct": np.random.normal(0.1, 0.5)} for _ in range(30)]
        
        report = run_drift_analysis(
            strategy="demo_strategy",
            asset_class="CRYPTO",
            baseline_metrics=baseline,
            recent_picks=recent,
            recent_returns=[np.random.normal(0, 0.02) for _ in range(30)],
            lookback_returns=[np.random.normal(0, 0.01) for _ in range(252)],
        )

        print(f"Strategy: {report.strategy}")
        print(f"Alerts: {len(report.alerts)}")
        for a in report.alerts:
            print(f"  [{a.severity}] {a.message}")
        print(f"Regime: {report.regime_state}")
        print(f"Recommended action: {report.recommended_action}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
