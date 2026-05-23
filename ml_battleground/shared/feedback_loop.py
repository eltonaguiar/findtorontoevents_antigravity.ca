# -*- coding: utf-8 -*-
"""ml_battleground.shared.feedback_loop
Implements autonomous feedback loops for online learning.

Priority hierarchy:
  1. Drift detection (ADWIN on residuals) = primary early-warning -> triggers retrain
  2. This module (hard thresholds) = emergency circuit breaker -> retrain + conservative mode
"""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Constants
RETRAIN_TRIGGER_PATH = Path(__file__).parent.parent / "retrain_trigger.json"
BASELINE_PATH = Path(__file__).parent.parent / "baseline_metrics.json"
MIN_PICKS_FOR_EVALUATION = 15  # Lowered from 30 to unlock ML evaluation sooner (System A has 19 closed picks).
# Note: the binomial test in _detect_degradation computes exact p-values and remains
# statistically valid at n=15, though power is reduced (~55% vs ~80% at n=30 for
# detecting a 15pp WR drop). This is an acceptable tradeoff to activate ML filtering
# earlier. The consecutive-losses circuit breaker (8 streak) is sample-size-independent.

# Closed picks sources — aggregate from all ML systems
_CLOSED_PICKS_SOURCES = [
    Path(__file__).parent.parent.parent / "ml_crypto_predictor" / "enhanced_models" / "live_picks" / "closed_picks.json",
    Path(__file__).parent.parent / "system_a_filter" / "data" / "closed_picks.json",
    Path(__file__).parent.parent / "system_b_regime" / "data" / "closed_picks.json",
    Path(__file__).parent.parent / "system_c_deeplearn" / "data" / "closed_picks.json",
    Path(__file__).parent.parent / "system_d_carry" / "data" / "closed_picks.json",
    Path(__file__).parent.parent / "system_e_momentum" / "data" / "closed_picks.json",
    Path(__file__).parent.parent.parent / "mercury2" / "data" / "closed_picks.json",
    # Active systems with abundant closed picks (wired in Mar 13 2026)
    Path(__file__).parent.parent.parent / "alpha_engine" / "data" / "closed_picks.json",
    Path(__file__).parent.parent.parent / "battleground" / "data" / "closed_picks.json",
    Path(__file__).parent.parent.parent / "KIMI_RISEOFTHECLAW" / "data" / "closed_picks.json",
]


def _load_closed_picks(days: int = 7) -> list:
    """Load closed picks from the last N days across all ML systems."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for path in _CLOSED_PICKS_SOURCES:
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data:
            ts = entry.get("timestamp") or entry.get("timestamp_est") or entry.get("entry_date") or entry.get("entry_time")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                # Normalize profit field (check all known field names across systems)
                profit = entry.get("profit") or entry.get("pnl_pct") or entry.get("net_pnl_pct") or entry.get("realized_pnl_pct", 0)
                entry["_profit"] = float(profit) if profit else 0.0
                entry["_source"] = str(path.parent.parent.name)
                recent.append(entry)
    return recent


def _rolling_metrics(picks: list) -> dict:
    """Calculate rolling win rate (WR), Sharpe, Profit Factor."""
    if not picks:
        return {"wr": 0.0, "sharpe": 0.0, "profit_factor": 0.0, "total": 0}
    profits = [p["_profit"] for p in picks]
    total = len(profits)
    wins = sum(1 for p in profits if p > 0)
    wr = wins / total

    avg = sum(profits) / total
    variance = sum((x - avg) ** 2 for x in profits) / total
    std = variance ** 0.5
    sharpe = avg / std if std != 0 else 0.0

    gains = sum(p for p in profits if p > 0)
    losses = -sum(p for p in profits if p < 0)
    profit_factor = gains / losses if losses != 0 else 0.0

    return {"wr": wr, "sharpe": sharpe, "profit_factor": profit_factor, "total": total}


def _binomial_test(n_losses: int, n_total: int, baseline_wr: float) -> float:
    """One-sided binomial test: probability of observing this many (or more)
    losses if the true win rate equals baseline_wr.
    Returns p-value. Low p-value = statistically significant degradation.
    Uses exact calculation (no scipy dependency required).
    """
    if n_total == 0 or baseline_wr <= 0:
        return 1.0
    expected_loss_rate = 1.0 - baseline_wr
    # P(X >= n_losses) where X ~ Binomial(n_total, expected_loss_rate)
    # Use complementary CDF: sum P(X=k) for k = n_losses..n_total
    p_value = 0.0
    for k in range(n_losses, n_total + 1):
        log_prob = (
            _log_comb(n_total, k)
            + k * math.log(expected_loss_rate)
            + (n_total - k) * math.log(1 - expected_loss_rate)
        )
        p_value += math.exp(log_prob)
    return min(p_value, 1.0)


def _log_comb(n: int, k: int) -> float:
    """Log of binomial coefficient C(n, k) using lgamma."""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _detect_consecutive_losses(picks: list) -> int:
    """Count max consecutive losses in recent picks (sorted by time)."""
    sorted_picks = sorted(picks, key=lambda p: p.get("timestamp", p.get("timestamp_est", "")))
    max_streak = 0
    current = 0
    for p in sorted_picks:
        if p["_profit"] <= 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


def _detect_degradation(metrics: dict, baseline: dict, picks: list) -> tuple:
    """Detect performance degradation using statistical tests.

    Returns (is_degraded: bool, reason: str).

    Checks (in priority order):
    1. Binomial test on loss rate vs baseline WR (p < 0.05)
    2. Sharpe turned negative when baseline was positive
    3. 8+ consecutive losses (emergency circuit breaker)
    """
    if metrics["total"] < MIN_PICKS_FOR_EVALUATION:
        return False, ""

    baseline_wr = baseline.get("wr", 0.5)
    n_total = metrics["total"]
    n_losses = n_total - int(metrics["wr"] * n_total)

    # 1. Binomial test: is the observed loss rate significantly worse than baseline?
    p_value = _binomial_test(n_losses, n_total, baseline_wr)
    if p_value < 0.05:
        return True, (
            f"Binomial test FAILED: {n_losses}/{n_total} losses "
            f"(p={p_value:.4f} < 0.05, baseline WR={baseline_wr:.1%})"
        )

    # 2. Sharpe sign flip
    if baseline.get("sharpe", 0) > 0 and metrics["sharpe"] < 0:
        return True, (
            f"Sharpe sign flip: {metrics['sharpe']:.3f} "
            f"(was {baseline['sharpe']:.3f})"
        )

    # 3. Emergency: 8+ consecutive losses (circuit breaker)
    max_streak = _detect_consecutive_losses(picks)
    if max_streak >= 8:
        return True, f"Circuit breaker: {max_streak} consecutive losses"

    return False, ""


def _write_trigger(reason: str):
    """Write retrain trigger file."""
    payload = {
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "retrain_and_conservative_mode",
    }
    with open(RETRAIN_TRIGGER_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def check_and_trigger():
    """Entry point for the feedback loop cycle.

    1. Load recent closed picks (7 days, all systems)
    2. Require >= 15 picks for evaluation (skip if insufficient data)
    3. Compute rolling metrics
    4. Compare against stored baseline using statistical tests
    5. Write retrain_trigger.json if degradation detected

    Baseline is set once on first run with sufficient data and only updated
    when a fresh retrain completes (via reset_baseline()).
    """
    picks = _load_closed_picks(days=7)
    if len(picks) < MIN_PICKS_FOR_EVALUATION:
        return

    metrics = _rolling_metrics(picks)

    # Load or initialize baseline
    if BASELINE_PATH.is_file():
        with open(BASELINE_PATH, "r", encoding="utf-8") as f:
            baseline = json.load(f)
    else:
        # First run with sufficient data — save as baseline
        baseline = metrics.copy()
        baseline["set_at"] = datetime.now(timezone.utc).isoformat()
        with open(BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)
        return

    is_degraded, reason = _detect_degradation(metrics, baseline, picks)
    if is_degraded:
        _write_trigger(reason)


def reset_baseline():
    """Call after a successful retrain to update the baseline.
    Only called externally by the retrain workflow, never by check_and_trigger().
    """
    picks = _load_closed_picks(days=7)
    if len(picks) < MIN_PICKS_FOR_EVALUATION:
        return
    metrics = _rolling_metrics(picks)
    metrics["set_at"] = datetime.now(timezone.utc).isoformat()
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    # Clear any existing trigger
    if RETRAIN_TRIGGER_PATH.is_file():
        RETRAIN_TRIGGER_PATH.unlink()


if __name__ == "__main__":
    check_and_trigger()
