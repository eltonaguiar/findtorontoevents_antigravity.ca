#!/usr/bin/env python3
"""
Advanced Risk Management System
================================
Combines volatility targeting, regime-aware Kelly sizing, Monte Carlo stress
testing, VaR enforcement, and drawdown recovery estimation.

Components:
  1. Dynamic Volatility Targeting — scale positions so portfolio vol stays at target
  2. Full Kelly with Regime Adjustment — aggressive in bull, defensive in bear
  3. Monte Carlo Stress Test — 1000 sims answering "is our edge real?"
  4. VaR Enforcement — halt new entries when tail risk is excessive
  5. Drawdown Recovery Calculator — estimate trades needed to recover
  6. run_full_risk_report() — compute all metrics on our 596 closed picks

Integration:
  - apply_advanced_risk_overlay() is called from production_scanner.py
    after Kelly sizer but before slippage model
  - Saves data/advanced_risk_report.json with full analysis

Pure Python + numpy. No sklearn/scipy.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# -- Windows UTF-8 fix --------------------------------------------------------
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# -- Paths --------------------------------------------------------------------
_ENGINE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _ENGINE_DIR / "data"
_ROOT = _ENGINE_DIR.parent

REPORT_PATH = _DATA_DIR / "advanced_risk_report.json"


# =============================================================================
# Helpers
# =============================================================================

def _load_json(path: Path):
    """Load JSON file, return empty list/dict on failure."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_json(path: Path, data) -> None:
    """Write JSON with NaN/Inf safety."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_sanitize(data), f, indent=2, default=str)
    except Exception as e:
        print(f"  [ADV-RISK] Could not write {path.name}: {e}")


def _sanitize(obj):
    """Recursively replace NaN/Infinity with None for JSON safety."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def _percentile_np(arr: np.ndarray, pct: float) -> float:
    """Compute percentile without scipy — pure numpy linear interpolation."""
    if len(arr) == 0:
        return 0.0
    sorted_arr = np.sort(arr)
    n = len(sorted_arr)
    k = (pct / 100.0) * (n - 1)
    lo = int(math.floor(k))
    hi = min(lo + 1, n - 1)
    frac = k - lo
    return float(sorted_arr[lo] + frac * (sorted_arr[hi] - sorted_arr[lo]))


def _load_closed_picks() -> list[dict]:
    """Load closed picks from available sources."""
    # Primary: dashboard_payload.json
    payload_path = _ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            closed = data.get("picks", {}).get("recent_closed", [])
            picks = [
                p for p in closed
                if p.get("pnl_pct") is not None
                and not p.get("_auto_expired", False)
            ]
            if picks:
                return picks
        except Exception:
            pass

    # Fallback: closed_picks.json
    fallback_path = _DATA_DIR / "closed_picks.json"
    if fallback_path.exists():
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                picks = json.load(f)
            return [p for p in picks if p.get("pnl_pct") is not None]
        except Exception:
            pass

    return []


def _load_active_picks() -> list[dict]:
    """Load active picks from available sources."""
    path = _DATA_DIR / "active_picks.json"
    data = _load_json(path)
    if isinstance(data, list):
        return data
    return []


def _get_regime() -> str:
    """Load current HMM regime from cached state file."""
    state_path = _DATA_DIR / "hmm_regime_state.json"
    try:
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            regime = data.get("regime", "CHOP")
            return regime.upper() if isinstance(regime, str) else "CHOP"
    except Exception:
        pass
    return "CHOP"


# =============================================================================
# 1. Dynamic Volatility Targeting
# =============================================================================

def vol_target_scaling(returns: np.ndarray, target_vol: float = 0.15,
                       lookback: int = 30, asset_class: str = "crypto") -> dict:
    """Scale position size so portfolio vol stays at target_vol.

    Args:
        returns: Array of daily returns (decimals, e.g., 0.02 = 2%)
        target_vol: Target annualized volatility (default 15%)
        lookback: Rolling window for realized vol computation
        asset_class: "crypto" (sqrt(365)) or "forex"/"equity" (sqrt(252))

    Returns:
        dict with realized_vol, annualized_vol, scale_factor, clamped_scale
    """
    annualization = math.sqrt(365) if asset_class == "crypto" else math.sqrt(252)

    if len(returns) < 5:
        return {
            "realized_vol_daily": 0.0,
            "annualized_vol": 0.0,
            "raw_scale": 1.0,
            "clamped_scale": 1.0,
            "target_vol": target_vol,
            "lookback_used": 0,
            "status": "insufficient_data",
        }

    # Use most recent `lookback` returns
    window = returns[-lookback:] if len(returns) > lookback else returns
    realized_vol_daily = float(np.std(window, ddof=1))
    annualized_vol = realized_vol_daily * annualization

    if annualized_vol <= 0:
        raw_scale = 1.0
    else:
        raw_scale = target_vol / annualized_vol

    # Clamp: never below 0.25x (still get exposure), never above 2.0x
    clamped_scale = max(0.25, min(2.0, raw_scale))

    return {
        "realized_vol_daily": round(realized_vol_daily, 6),
        "annualized_vol": round(annualized_vol, 4),
        "raw_scale": round(raw_scale, 4),
        "clamped_scale": round(clamped_scale, 4),
        "target_vol": target_vol,
        "lookback_used": len(window),
        "status": "active",
    }


# =============================================================================
# 2. Full Kelly with Regime Adjustment
# =============================================================================

def regime_kelly(win_rate: float, avg_win: float, avg_loss: float,
                 regime: str = "CHOP") -> dict:
    """Full Kelly fraction with regime-based scaling.

    Args:
        win_rate: Historical win rate (0.0 - 1.0)
        avg_win: Average winning trade return (decimal, e.g., 0.05 = 5%)
        avg_loss: Average losing trade loss (decimal, positive, e.g., 0.03 = 3%)
        regime: "BULL", "BEAR", or "CHOP"

    Returns:
        dict with full_kelly, regime_fraction, regime_scaled, final_size_pct
    """
    # Regime scaling map
    regime_scale = {"BULL": 0.50, "BEAR": 0.25, "CHOP": 0.10}
    scale = regime_scale.get(regime.upper(), 0.10)

    if avg_win <= 0 or avg_loss <= 0:
        return {
            "full_kelly": 0.0,
            "regime": regime,
            "regime_fraction": scale,
            "regime_scaled_kelly": 0.0,
            "final_size_pct": 0.5,
            "capped": False,
            "status": "no_edge_data",
        }

    # Full Kelly formula: f* = (WR * avg_win - (1-WR) * avg_loss) / avg_win
    full_kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

    if full_kelly <= 0:
        return {
            "full_kelly": round(full_kelly, 6),
            "regime": regime,
            "regime_fraction": scale,
            "regime_scaled_kelly": 0.0,
            "final_size_pct": 0.5,
            "capped": False,
            "status": "negative_edge",
        }

    # Apply regime scaling
    regime_scaled = full_kelly * scale

    # Cap at 5% of portfolio per trade (hard risk limit)
    capped = regime_scaled > 0.05
    final_pct = min(regime_scaled, 0.05) * 100  # as percentage

    # Floor at 0.5% (minimum skin in the game)
    final_pct = max(0.5, final_pct)

    return {
        "full_kelly": round(full_kelly, 6),
        "regime": regime,
        "regime_fraction": scale,
        "regime_scaled_kelly": round(regime_scaled, 6),
        "final_size_pct": round(final_pct, 2),
        "capped": capped,
        "status": "active",
    }


# =============================================================================
# 3. Monte Carlo Stress Test
# =============================================================================

def monte_carlo_stress(closed_pnls: list[float], n_sims: int = 1000,
                       n_trades: int = 100, seed: int = 42) -> dict:
    """Monte Carlo stress test via bootstrap resampling.

    For each simulation: randomly sample n_trades from closed_pnls with
    replacement, compute cumulative PnL, max drawdown, final equity.

    Reports 5th/25th/50th/75th/95th percentiles — answers:
    "What's the worst 5% outcome over 100 trades?"

    Args:
        closed_pnls: List of PnL percentages from closed trades
        n_sims: Number of simulations (default 1000)
        n_trades: Number of trades per simulation path
        seed: Random seed for reproducibility

    Returns:
        dict with percentiles, edge analysis, luck assessment
    """
    if len(closed_pnls) < 5:
        return {
            "status": "insufficient_data",
            "n_closed": len(closed_pnls),
            "message": "Need at least 5 closed trades for Monte Carlo",
        }

    rng = np.random.default_rng(seed=seed)
    pnls = np.array(closed_pnls, dtype=np.float64)

    # Pre-allocate result arrays
    final_equities = np.zeros(n_sims)
    max_drawdowns = np.zeros(n_sims)
    peak_equities = np.zeros(n_sims)
    worst_streaks = np.zeros(n_sims, dtype=np.int64)

    for i in range(n_sims):
        # Bootstrap: sample with replacement
        sampled = rng.choice(pnls, size=n_trades, replace=True)

        # Compute equity curve (starting at 100%)
        equity = np.cumprod(1.0 + sampled / 100.0) * 100.0

        final_equities[i] = equity[-1]

        # Max drawdown
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max * 100.0
        max_drawdowns[i] = float(np.min(drawdowns))  # Most negative = worst DD

        peak_equities[i] = float(np.max(equity))

        # Worst losing streak
        is_loss = sampled < 0
        streak = 0
        worst = 0
        for loss in is_loss:
            if loss:
                streak += 1
                worst = max(worst, streak)
            else:
                streak = 0
        worst_streaks[i] = worst

    # Compute percentiles
    pctiles = [5, 25, 50, 75, 95]
    equity_pctiles = {f"p{p}": round(_percentile_np(final_equities, p), 2)
                      for p in pctiles}
    dd_pctiles = {f"p{p}": round(_percentile_np(max_drawdowns, p), 2)
                  for p in pctiles}
    streak_pctiles = {f"p{p}": int(_percentile_np(worst_streaks.astype(float), p))
                      for p in pctiles}

    # Edge analysis
    actual_mean = float(np.mean(pnls))
    actual_win_rate = float(np.sum(pnls > 0) / len(pnls)) if len(pnls) > 0 else 0
    n_profitable_sims = int(np.sum(final_equities > 100.0))
    profit_probability = n_profitable_sims / n_sims

    # Is our edge real or could it be luck?
    # If >80% of simulations are profitable, edge is likely real
    if profit_probability >= 0.80:
        luck_assessment = "EDGE_CONFIRMED"
        luck_detail = (f"{profit_probability:.0%} of {n_sims} simulations ended profitable. "
                       f"Edge is statistically robust.")
    elif profit_probability >= 0.60:
        luck_assessment = "EDGE_PROBABLE"
        luck_detail = (f"{profit_probability:.0%} profitable sims. Edge likely real but "
                       f"not overwhelmingly strong. Continue monitoring.")
    elif profit_probability >= 0.45:
        luck_assessment = "INCONCLUSIVE"
        luck_detail = (f"{profit_probability:.0%} profitable sims. Cannot distinguish "
                       f"from random chance. Need more data or better strategies.")
    else:
        luck_assessment = "NO_EDGE"
        luck_detail = (f"{profit_probability:.0%} profitable sims. Current strategy mix "
                       f"is not generating a reliable edge.")

    # Risk of ruin: probability that any sim drops below 50% equity
    ruin_count = int(np.sum(final_equities < 50.0))
    ruin_probability = ruin_count / n_sims

    return {
        "status": "complete",
        "n_sims": n_sims,
        "n_trades_per_sim": n_trades,
        "n_closed_picks_sampled": len(closed_pnls),
        "actual_stats": {
            "mean_pnl_pct": round(actual_mean, 4),
            "win_rate": round(actual_win_rate, 4),
            "total_trades": len(closed_pnls),
        },
        "final_equity_percentiles": equity_pctiles,
        "max_drawdown_percentiles": dd_pctiles,
        "worst_losing_streak_percentiles": streak_pctiles,
        "profit_probability": round(profit_probability, 4),
        "ruin_probability": round(ruin_probability, 4),
        "worst_5pct_equity": equity_pctiles["p5"],
        "worst_5pct_drawdown": dd_pctiles["p5"],
        "median_final_equity": equity_pctiles["p50"],
        "best_5pct_equity": equity_pctiles["p95"],
        "luck_assessment": luck_assessment,
        "luck_detail": luck_detail,
        "edge_question": "Is our edge real or could it be luck?",
        "edge_answer": luck_detail,
    }


# =============================================================================
# 4. VaR Enforcement (integrates with existing var_enforcer.py)
# =============================================================================

def daily_var_check(active_picks: list[dict], prices: dict[str, float] | None = None,
                    portfolio_value: float = 10000) -> dict:
    """Compute current portfolio VaR at 95% and 99%.

    Rules:
      - If VaR(95%) > 2% of portfolio: reduce all positions by (VaR/target_var)
      - If VaR(99%) > 5%: HALT all new entries

    Args:
        active_picks: Currently open positions
        prices: Optional dict of symbol -> current_price
        portfolio_value: Total portfolio value in dollars

    Returns:
        dict with var_95, var_99, action, scaling_factor
    """
    if not active_picks:
        return {
            "var_95_pct": 0.0,
            "var_99_pct": 0.0,
            "action": "NO_POSITIONS",
            "scaling_factor": 1.0,
            "halt_new_entries": False,
            "n_positions": 0,
        }

    # Collect unrealized PnL percentages as proxy for position risk
    position_risks = []
    for pick in active_picks:
        # Use the pick's stop-loss distance as worst-case risk per position
        entry = float(pick.get("entry_price", 0) or 0)
        sl = float(pick.get("stop_loss", 0) or 0)
        if entry > 0 and sl > 0:
            direction = pick.get("direction", "LONG")
            if direction == "LONG":
                risk_pct = (entry - sl) / entry
            else:
                risk_pct = (sl - entry) / entry
            position_risks.append(abs(risk_pct))
        else:
            # Default 3% risk if no SL
            position_risks.append(0.03)

    if not position_risks:
        return {
            "var_95_pct": 0.0,
            "var_99_pct": 0.0,
            "action": "NO_RISK_DATA",
            "scaling_factor": 1.0,
            "halt_new_entries": False,
            "n_positions": 0,
        }

    risk_arr = np.array(position_risks)
    n_positions = len(risk_arr)

    # Portfolio VaR via parametric method (assumes normal, conservative for crypto)
    # Aggregate: average position risk * sqrt(n) for correlation adjustment
    mean_risk = float(np.mean(risk_arr))
    # Assume average pairwise correlation of 0.5 for crypto
    rho = 0.5
    portfolio_vol = mean_risk * math.sqrt(n_positions * (1 + (n_positions - 1) * rho) / n_positions)

    # VaR = portfolio_vol * z_score
    z_95 = 1.645  # 95th percentile z-score
    z_99 = 2.326  # 99th percentile z-score

    var_95 = portfolio_vol * z_95 * 100  # as percentage
    var_99 = portfolio_vol * z_99 * 100

    # Decision logic
    target_var_95 = 2.0  # 2% of portfolio
    target_var_99 = 5.0  # 5% of portfolio

    halt_new = var_99 > target_var_99
    scaling_factor = 1.0
    action = "NORMAL"

    if halt_new:
        action = "HALT_NEW_ENTRIES"
        scaling_factor = target_var_99 / var_99 if var_99 > 0 else 0.5
    elif var_95 > target_var_95:
        action = "REDUCE_POSITIONS"
        scaling_factor = target_var_95 / var_95 if var_95 > 0 else 0.75

    scaling_factor = max(0.1, min(1.0, scaling_factor))

    return {
        "var_95_pct": round(var_95, 4),
        "var_99_pct": round(var_99, 4),
        "action": action,
        "scaling_factor": round(scaling_factor, 4),
        "halt_new_entries": halt_new,
        "n_positions": n_positions,
        "mean_position_risk_pct": round(mean_risk * 100, 2),
        "portfolio_vol_pct": round(portfolio_vol * 100, 2),
        "target_var_95": target_var_95,
        "target_var_99": target_var_99,
    }


# =============================================================================
# 5. Drawdown Recovery Calculator
# =============================================================================

def drawdown_recovery(current_dd_pct: float, win_rate: float,
                      avg_win_pct: float, avg_loss_pct: float = 0.0) -> dict:
    """Estimate trades needed to recover from current drawdown.

    Uses expected value per trade to compute recovery trades.
    At 60% WR and 3% avg win, 2% avg loss: EV = 0.6*3 - 0.4*2 = 1.0% per trade
    10% DD / 1.0% EV = 10 trades.

    Args:
        current_dd_pct: Current drawdown as positive percentage (e.g., 10 = 10%)
        win_rate: Win rate (0.0 - 1.0)
        avg_win_pct: Average win percentage (positive number)
        avg_loss_pct: Average loss percentage (positive number, loss magnitude)

    Returns:
        dict with estimated trades, confidence range, dashboard label
    """
    if current_dd_pct <= 0:
        return {
            "current_dd_pct": 0.0,
            "trades_to_recover": 0,
            "recovery_label": "No drawdown",
            "ev_per_trade_pct": 0.0,
            "status": "no_drawdown",
        }

    if avg_loss_pct <= 0:
        avg_loss_pct = avg_win_pct * 0.5  # default assumption

    # Expected value per trade
    ev_per_trade = win_rate * avg_win_pct - (1 - win_rate) * avg_loss_pct

    if ev_per_trade <= 0:
        return {
            "current_dd_pct": round(current_dd_pct, 2),
            "trades_to_recover": -1,
            "recovery_label": "Cannot recover (negative EV)",
            "ev_per_trade_pct": round(ev_per_trade, 4),
            "status": "negative_ev",
        }

    # Base estimate
    trades_needed = math.ceil(current_dd_pct / ev_per_trade)

    # Confidence range: variance makes recovery uncertain
    # Optimistic: 70% of expected trades; Pessimistic: 180%
    optimistic = max(1, math.ceil(trades_needed * 0.7))
    pessimistic = math.ceil(trades_needed * 1.8)

    label = f"Est. recovery: ~{trades_needed} trades"
    if trades_needed > 50:
        label = f"Est. recovery: ~{trades_needed} trades (extended)"

    return {
        "current_dd_pct": round(current_dd_pct, 2),
        "trades_to_recover": trades_needed,
        "trades_optimistic": optimistic,
        "trades_pessimistic": pessimistic,
        "recovery_label": label,
        "ev_per_trade_pct": round(ev_per_trade, 4),
        "win_rate": round(win_rate, 4),
        "avg_win_pct": round(avg_win_pct, 4),
        "avg_loss_pct": round(avg_loss_pct, 4),
        "status": "estimated",
    }


# =============================================================================
# 6. Full Risk Report on Closed Picks
# =============================================================================

def run_full_risk_report(save: bool = True) -> dict:
    """Run the complete advanced risk analysis on our actual closed picks.

    Computes:
      - Volatility targeting metrics
      - Regime-aware Kelly sizing
      - Monte Carlo stress test (1000 sims)
      - VaR check on active positions
      - Drawdown recovery estimate

    Reports: "Is our edge real or could it be luck?"

    Returns:
        Full risk report dict (also saved to data/advanced_risk_report.json)
    """
    print("[ADV-RISK] Running full advanced risk report...")

    # Load closed picks
    closed = _load_closed_picks()
    n_closed = len(closed)
    print(f"  [ADV-RISK] Loaded {n_closed} closed picks")

    # Extract PnL array
    pnl_list = [float(p.get("pnl_pct", 0) or 0) for p in closed]
    pnl_arr = np.array(pnl_list, dtype=np.float64)

    # Compute basic stats
    wins = [x for x in pnl_list if x > 0]
    losses = [x for x in pnl_list if x <= 0]
    win_rate = len(wins) / n_closed if n_closed > 0 else 0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = abs(float(np.mean(losses))) if losses else 0.0

    print(f"  [ADV-RISK] WR={win_rate:.1%} | Avg Win={avg_win:.2f}% | Avg Loss={avg_loss:.2f}%")

    # --- 1. Volatility Targeting ---
    print("  [ADV-RISK] Computing volatility targeting...")
    # Treat each PnL as a "daily return" for vol calculation
    vol_result = vol_target_scaling(
        pnl_arr / 100.0,  # Convert percentage to decimal
        target_vol=0.15,
        lookback=30,
        asset_class="crypto",
    )

    # --- 2. Regime Kelly ---
    print("  [ADV-RISK] Computing regime-aware Kelly sizing...")
    current_regime = _get_regime()
    kelly_result = regime_kelly(
        win_rate=win_rate,
        avg_win=avg_win / 100.0,  # Convert to decimal
        avg_loss=avg_loss / 100.0,
        regime=current_regime,
    )

    # --- 3. Monte Carlo Stress Test ---
    print(f"  [ADV-RISK] Running Monte Carlo stress test (1000 sims x 100 trades)...")
    t0 = time.time()
    mc_result = monte_carlo_stress(pnl_list, n_sims=1000, n_trades=100)
    mc_elapsed = time.time() - t0
    print(f"  [ADV-RISK] Monte Carlo complete in {mc_elapsed:.1f}s")
    print(f"  [ADV-RISK] Edge verdict: {mc_result.get('luck_assessment', 'N/A')}")

    # --- 4. VaR Check ---
    print("  [ADV-RISK] Computing VaR enforcement...")
    active = _load_active_picks()
    portfolio_val = float(os.environ.get("ALPHA_PORTFOLIO_VALUE", "10000"))
    var_result = daily_var_check(active, portfolio_value=portfolio_val)
    print(f"  [ADV-RISK] VaR(95%)={var_result['var_95_pct']:.2f}% | "
          f"Action={var_result['action']}")

    # --- 5. Drawdown Recovery ---
    print("  [ADV-RISK] Computing drawdown recovery estimate...")
    # Compute current drawdown from equity curve
    equity_curve = np.cumprod(1.0 + pnl_arr / 100.0) * 100.0
    if len(equity_curve) > 0:
        peak = float(np.maximum.accumulate(equity_curve)[-1])
        current = float(equity_curve[-1])
        current_dd = max(0, (peak - current) / peak * 100)
    else:
        current_dd = 0.0

    dd_result = drawdown_recovery(
        current_dd_pct=current_dd,
        win_rate=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
    )
    print(f"  [ADV-RISK] {dd_result['recovery_label']}")

    # --- Per-category breakdown ---
    print("  [ADV-RISK] Computing per-category Monte Carlo...")
    category_results = {}
    for cat in ["crypto", "forex", "equity"]:
        cat_pnls = [float(p.get("pnl_pct", 0) or 0)
                    for p in closed if p.get("category") == cat]
        if len(cat_pnls) >= 5:
            cat_mc = monte_carlo_stress(cat_pnls, n_sims=500, n_trades=50, seed=42)
            cat_wins = [x for x in cat_pnls if x > 0]
            cat_losses = [x for x in cat_pnls if x <= 0]
            category_results[cat] = {
                "n_trades": len(cat_pnls),
                "win_rate": round(len(cat_wins) / len(cat_pnls), 4),
                "avg_win": round(float(np.mean(cat_wins)), 4) if cat_wins else 0.0,
                "avg_loss": round(abs(float(np.mean(cat_losses))), 4) if cat_losses else 0.0,
                "monte_carlo": cat_mc,
            }
            print(f"    [{cat.upper()}] {len(cat_pnls)} trades | "
                  f"Edge: {cat_mc.get('luck_assessment', 'N/A')}")

    # --- Per-strategy top/bottom ---
    print("  [ADV-RISK] Identifying best/worst strategies by edge strength...")
    strategy_edge = {}
    for p in closed:
        strat = p.get("strategy", "unknown")
        if strat not in strategy_edge:
            strategy_edge[strat] = []
        strategy_edge[strat].append(float(p.get("pnl_pct", 0) or 0))

    strategy_scores = []
    for strat, strat_pnls in strategy_edge.items():
        if len(strat_pnls) >= 5:
            s_wins = [x for x in strat_pnls if x > 0]
            s_wr = len(s_wins) / len(strat_pnls)
            s_mean = float(np.mean(strat_pnls))
            # Quick edge score: mean PnL * sqrt(n) (t-stat proxy)
            s_edge = s_mean * math.sqrt(len(strat_pnls))
            strategy_scores.append({
                "strategy": strat,
                "n_trades": len(strat_pnls),
                "win_rate": round(s_wr, 4),
                "mean_pnl": round(s_mean, 4),
                "edge_score": round(s_edge, 4),
            })

    strategy_scores.sort(key=lambda x: x["edge_score"], reverse=True)
    top_5_strategies = strategy_scores[:5]
    bottom_5_strategies = strategy_scores[-5:] if len(strategy_scores) >= 5 else strategy_scores

    # --- Assemble report ---
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_closed_picks": n_closed,
            "overall_win_rate": round(win_rate, 4),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "current_regime": current_regime,
            "edge_verdict": mc_result.get("luck_assessment", "UNKNOWN"),
            "edge_detail": mc_result.get("luck_detail", ""),
            "profit_probability": mc_result.get("profit_probability", 0),
            "ruin_probability": mc_result.get("ruin_probability", 0),
        },
        "volatility_targeting": vol_result,
        "regime_kelly": kelly_result,
        "monte_carlo_stress_test": mc_result,
        "var_enforcement": var_result,
        "drawdown_recovery": dd_result,
        "category_breakdown": category_results,
        "top_5_strategies_by_edge": top_5_strategies,
        "bottom_5_strategies_by_edge": bottom_5_strategies,
    }

    if save:
        _save_json(REPORT_PATH, report)
        print(f"  [ADV-RISK] Report saved to {REPORT_PATH.name}")

    print(f"[ADV-RISK] Complete. Edge verdict: {report['summary']['edge_verdict']}")
    return report


# =============================================================================
# 7. Production Scanner Integration — Position Sizing Overlay
# =============================================================================

def apply_advanced_risk_overlay(active_picks: list[dict],
                                portfolio_value: float = 10000) -> list[dict]:
    """Apply vol-target and regime-Kelly as position sizing overlay.

    Called from production_scanner.py AFTER Kelly sizer but BEFORE slippage model.
    Adjusts kelly_position_size_usd and adds advanced_risk metadata.

    Args:
        active_picks: List of active pick dicts (already Kelly-sized)
        portfolio_value: Portfolio value in dollars

    Returns:
        Modified active_picks with advanced risk adjustments
    """
    if not active_picks:
        return active_picks

    # Load closed picks for vol computation
    closed = _load_closed_picks()
    pnl_list = [float(p.get("pnl_pct", 0) or 0) for p in closed]
    pnl_arr = np.array(pnl_list, dtype=np.float64) / 100.0 if pnl_list else np.array([])

    # Compute vol-target scale
    vol_info = vol_target_scaling(pnl_arr, target_vol=0.15, lookback=30,
                                  asset_class="crypto")
    vol_scale = vol_info["clamped_scale"]

    # Get regime for Kelly
    regime = _get_regime()

    # Compute portfolio-level stats
    wins = [x for x in pnl_list if x > 0]
    losses = [x for x in pnl_list if x <= 0]
    n_closed = len(pnl_list)
    win_rate = len(wins) / n_closed if n_closed > 0 else 0.5
    avg_win = abs(float(np.mean(wins))) / 100.0 if wins else 0.03
    avg_loss = abs(float(np.mean(losses))) / 100.0 if losses else 0.02

    # Compute regime-Kelly
    kelly_info = regime_kelly(win_rate, avg_win, avg_loss, regime)
    kelly_size_pct = kelly_info["final_size_pct"] / 100.0  # Convert to fraction

    # VaR check
    var_info = daily_var_check(active_picks, portfolio_value=portfolio_value)
    var_scale = var_info["scaling_factor"]
    halt_new = var_info["halt_new_entries"]

    # Combined scaling: vol_target * var_enforcement
    combined_scale = vol_scale * var_scale
    combined_scale = max(0.1, min(2.0, combined_scale))

    adjusted_count = 0
    for pick in active_picks:
        # Apply regime-Kelly sizing if current Kelly fraction exists
        current_kelly = float(pick.get("kelly_fraction", 0) or 0)
        if current_kelly > 0:
            # Blend: weight towards regime-Kelly but don't fully override
            blended_kelly = (current_kelly + kelly_size_pct) / 2.0
        else:
            blended_kelly = kelly_size_pct

        # Apply vol-target + VaR scaling to position size
        current_size = float(pick.get("kelly_position_size_usd", 0) or 0)
        if current_size > 0:
            new_size = current_size * combined_scale
        else:
            new_size = portfolio_value * blended_kelly * combined_scale

        # Hard cap: never more than 5% of portfolio per position
        max_size = portfolio_value * 0.05
        new_size = min(new_size, max_size)

        # Floor: at least $50 (minimum viable position)
        new_size = max(50.0, new_size)

        pick["kelly_position_size_usd"] = round(new_size, 2)
        pick["kelly_fraction"] = round(blended_kelly, 6)

        # Add metadata
        pick["adv_risk_vol_scale"] = vol_scale
        pick["adv_risk_var_scale"] = var_scale
        pick["adv_risk_combined_scale"] = round(combined_scale, 4)
        pick["adv_risk_regime"] = regime
        pick["adv_risk_regime_kelly_pct"] = kelly_info["final_size_pct"]
        pick["adv_risk_halt_new"] = halt_new

        adjusted_count += 1

    print(f"  [ADV-RISK] Overlay applied to {adjusted_count} picks | "
          f"vol_scale={vol_scale:.2f} var_scale={var_scale:.2f} "
          f"combined={combined_scale:.2f} regime={regime}")

    return active_picks


# =============================================================================
# CLI entry point
# =============================================================================

if __name__ == "__main__":
    report = run_full_risk_report(save=True)

    print("\n" + "=" * 70)
    print("ADVANCED RISK REPORT SUMMARY")
    print("=" * 70)
    s = report["summary"]
    print(f"  Closed picks analyzed: {s['total_closed_picks']}")
    print(f"  Win rate: {s['overall_win_rate']:.1%}")
    print(f"  Avg win: {s['avg_win_pct']:.2f}%  |  Avg loss: {s['avg_loss_pct']:.2f}%")
    print(f"  Current regime: {s['current_regime']}")
    print(f"  Edge verdict: {s['edge_verdict']}")
    print(f"  Profit probability: {s['profit_probability']:.1%}")
    print(f"  Ruin probability: {s['ruin_probability']:.1%}")

    mc = report["monte_carlo_stress_test"]
    if mc.get("status") == "complete":
        print(f"\n  Monte Carlo (1000 sims x 100 trades):")
        print(f"    Worst 5%:  equity={mc['worst_5pct_equity']:.1f}  DD={mc['worst_5pct_drawdown']:.1f}%")
        print(f"    Median:    equity={mc['median_final_equity']:.1f}")
        print(f"    Best 5%:   equity={mc['best_5pct_equity']:.1f}")

    vt = report["volatility_targeting"]
    print(f"\n  Vol Targeting: annualized={vt['annualized_vol']:.1%}  scale={vt['clamped_scale']:.2f}x")

    rk = report["regime_kelly"]
    print(f"  Regime Kelly: {rk['regime']} -> {rk['final_size_pct']:.1f}% per trade")

    var = report["var_enforcement"]
    print(f"  VaR(95%): {var['var_95_pct']:.2f}%  |  Action: {var['action']}")

    dd = report["drawdown_recovery"]
    print(f"  Drawdown: {dd['recovery_label']}")

    print("\n  " + "-" * 40)
    print(f"  ANSWER: {s['edge_detail']}")
    print("=" * 70)
